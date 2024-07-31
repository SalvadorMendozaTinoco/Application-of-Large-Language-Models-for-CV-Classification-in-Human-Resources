# Paso 1: Cargar las bibliotecas necesarias
import os

import bson
from colorama import Back, Fore, Style, init
from dotenv import dotenv_values
from joblib import Parallel, delayed
from langchain_anthropic import ChatAnthropic
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from pymongo import MongoClient

from cryptography_utils import calculate_md5, create_env_file
from extract_features import (
    embed_certifications,
    embed_education,
    embed_works,
    extract_resume_features,
)
from extractClass import Extractor

# Paso 2: Aquí verificamos que las variables de entorno estén configuradas correctamente
# para poder utilizar los servicios de terceros, en este caso, MongoDB, Anthropic y Azure.
# ------------------- .env -------------------
init(autoreset=True)
if not os.path.exists(".env"):
    try:
        print(
            "\n-> "
            + Back.GREEN
            + Fore.BLACK
            + "Parece que aún no se ha creado el archivo .env,\n por favor ingrese la contraseña para crearlo:",
            end="",
        )
        create_env_file()
    except Exception as e:
        print(Fore.RED + f"❌ Error al crear el archivo .env ❌")
        print(Fore.RED + f" {e} ")
        raise SystemExit

# ------------------- End of .env -------------------
# Paso 3: Mostramos en pantalla un mensaje de bienvenida y le pedimos confirmación al usuario
# sobre los directorios que se van a procesar.
# ------------------- Greetings -------------------
print(Fore.GREEN + "\n\tResume Parser para PISA Equipo")
# Detect all directories in the resumes folder
directories = [
    name
    for name in os.listdir("resumes")
    if os.path.isdir(os.path.join("resumes", name))
]

print(Fore.CYAN + "ℹ️ Se han encontrado los siguientes directorios ℹ️")
files = {}
for index, directory in enumerate(directories):
    files[directories[index]] = os.listdir(f"resumes/{directory}")
    print(f"  {index + 1}. {directory}\t ({len(files[directories[index]])} documentos)")
del index, directories


while True:
    input_dir = input(
        "\n-> "
        + Back.GREEN
        + Fore.BLACK
        + "Quieres continuar con estos directorios? [Y/n]:"
        + Style.RESET_ALL
        + " "
    )
    if input_dir.lower() == "n" or input_dir.lower() == "no":
        raise SystemExit
    if input_dir.lower() == "y" or input_dir.lower() == "yes":
        break

# ------------------- End of Greetings -------------------

# Paso 4: Configuramos el cliente de MongoDB para poder insertar los documentos procesados.
# Además, iniciamos una sesión con el modelo de lenguaje de Anthropic, en este caso, Claude-3-haiku-20240307,
# esta sesión va con una configuración personalizada para realizar una tarea de extracción en los documentos.
# Por último, cargamos el modelo de embeddings sBERT, en este caso Alibaba-NLP/gte-base-en-v1.5.

# ------------------- General Configuration -------------------
print(Fore.CYAN + f"\n    ℹ️ Cargando configuración inicial ℹ️")
print("⏳ Esto puede tardar un poco, por favor espere. ⌛")
config = dotenv_values(".env")
extract_client = Extractor(overwrite_env="prod")
chat = ChatAnthropic(
    temperature=0,
    api_key=(
        config.get("ANTHROPIC_TEST_API_KEY", None)
        if config.get("CURRENT_ENV", "dev") == "dev"
        else config["ANTHROPIC_API_KEY"]
    ),
    model_name="claude-3-haiku-20240307",
    max_tokens=4096,
)
system = """You are a bilingual virtual assistant who knows both English and Spanish. 
Your task will be to extract information from resumes contained in the following user message. Once you have extracted 
all the information required from the next message, you should provide your answer in English. You must use the following template in your answer:
Type:[Work Experience / Education / Certification]
Management:[This field applies only for work experience, if the activity was mainly focused on team management, write Yes, if not, write No]
Title:[Title translated to english, if only education is available, use the education degree level instead of the full name, e.g. Bachelors Degree, Masters, Doctoral, etc.]
Institution:[Institution]
Start Date:[Start Date in format: Month, Year(If unknown write NA)]
End Date:[End Date in format: Month, Year(If unknown write NA, if current write Present)]
Brief:[Short explanation (should have a maximum of 40 words) in english of the work experience, leave out any specifics. Avoid using the pronouns he or she, preferably use candidate when possible]
If you read more than one work experience or education, please separate them with a "\\n" and use the following format for each one.
Priorize parsing education. Do not skip any Work Experience or Education.
"""
human = "{text}"
prompt = ChatPromptTemplate.from_messages([("system", system), ("human", human)])
chain = prompt | chat
embeddings = HuggingFaceEmbeddings(
    model_name="Alibaba-NLP/gte-base-en-v1.5",
    model_kwargs={"device": "cpu", "trust_remote_code": True},
    encode_kwargs={"normalize_embeddings": True},
)
documentClient = MongoClient(config["MONGO_DOCS_URI"])
cE = documentClient["pisa"]["embedded"]
# ------------------- End of General Configuration -------------------
# Paso 5: Establecemos conexión con otra base de datos de MongoDB, en este caso, 
# para llevar un registro de los documentos basado en su hash. Esta base de datos ayudará a poder reanudar 
# el proceso en caso de que ocurra un error en el procesamiento de los documentos.
# Además, de proporcionar información sobre el estado de los documentos procesados. 
# ------------------- Tracker Configuration -------------------
print(Fore.CYAN + f"\n    ℹ️ Configurando tracker en MongoDB ℹ️")
print("⏳ Esto puede tardar un poco, por favor espere. ⌛")
tracker_client = MongoClient(config["MONGO_TRACKER_URI"])
tracker_db = tracker_client["pisa"]["tracker"]


def process_file(directory, file):
    current_hash = calculate_md5(f"resumes/{directory}/{file}")
    if current_hash is False:
        return None, None, None
    existing_document = tracker_db.find_one({"hash": current_hash})
    if existing_document is None:
        return (
            {
                "hash": current_hash,
                "directory": directory,
                "filename": file,
                "status": "pending",
            },
            file,
            directory,
        )
    elif existing_document["status"] == "pending":
        return None, file, directory
    elif existing_document["status"] == "failed":
        print(
            Fore.RED
            + "Ups 🙈, parece que se encontró un error previo,\n es necesario cambiar su estado fuera del flujo",
            Fore.YELLOW + file,
        )
        return None, None, None
    else:
        return None, None, None


unprocessed = {k: [] for k in files.keys()}
results = Parallel(n_jobs=-1, prefer="threads")(
    delayed(process_file)(directory, file)
    for directory in files
    for file in files[directory]
)

documents_to_insert = [result[0] for result in results if result[0] is not None]
for result in results:
    if result[1] is not None:
        unprocessed[result[2]].append(result[1])

# Insert all documents in a single operation
if documents_to_insert:
    tracker_db.insert_many(documents_to_insert)

del documents_to_insert, results, process_file, files, directory
# ------------------- End of Tracker Configuration -------------------
# Paso 6: Procesar los documentos que no se han procesado previamente:
# 6.1. Extraer el texto de los documentos: Para esto usamos diferentes técnicas de extracción de texto. 
# Estas técnicas se pueden consultar a mayor detalle en el archivo extractClass.py. Pero en resumen, el flujo normal
# será tratar de extraer el texto de manera ingenua de manera local, si no se puede, se intentará extraer el texto
# utilizando el servicio de Azure.
# 6.2. Procesar el texto extraído: Una vez que se tiene el texto extraído, se procede a categorizar la información
# en diferentes categorías, como trabajo, educación, certificaciones, etc. Además, se extraen características como
# años de experiencia, años de experiencia en gestión, tiempo promedio en un trabajo, etc.
# Para el texto extraído se utiliza el modelo de lenguaje de Anthropic, en este caso, Claude-3-haiku-20240307.
# Procesar el texto así trae una ventajas significativas pues nos desaremos de características que pueden inducir
# a sesgos en el futuro, puesto que el modelo del lenguaje ayuda a estandarizar el lenguaje volviendo todo el texto
# al idioma inglés, quitando cualquier tipo de género, etc. Posteriormente, se calcula un embedding para todos los
# datos de texto y se normalizan. Finalmente, se insertan los datos en la base de datos de MongoDB.
# 6.3. Actualizar el estado de los documentos procesados: Una vez que se ha procesado un documento, se actualiza su
# estado en la base de datos de MongoDB, indicando que ya ha sido procesado y si hubo algún error, se registra el error.
# ------------------- Process Documents -------------------
def process_cv(
    path: str,
    file: str,
    verbose_tokens: bool = False,
    upload_mongo: bool = True,
):
    try:
        current_hash = calculate_md5(path + file)
        if current_hash is False:
            raise Exception("Failed to calculate MD5")

        createdAt, allText = extract_client.extract(
            path + file, azure=True, return_created_at=True
        )

        output = chain.invoke({"text": allText})
        if verbose_tokens:
            tokens = output.response_metadata["usage"]
            lectura = 0.25 / 1000000 * 17.05 * tokens["input_tokens"]
            escritura = 1.25 / 1000000 * 17.05 * tokens["output_tokens"]
            print(
                "Costo de lectura: ${} ({} tokens) \nCosto de escritura ${} ({} tokens)\nTotal ${}".format(
                    lectura,
                    tokens["input_tokens"],
                    escritura,
                    tokens["output_tokens"],
                    lectura + escritura,
                )
            )

        (
            work,
            education,
            certification,
            expYears,
            expYearsManagement,
            avgTimeInJob,
        ) = extract_resume_features(output.content, createdAt)

        embedded_work = embed_works(work, embeddings)
        embedded_cert = embed_certifications(certification, embeddings)
        embedded_edu = embed_education(education, embeddings)

        datos = {
            "file": f"{file}//{current_hash}",
            "work": work,
            "education": education,
            "certification": certification,
            "label": path,
        }
        datos_bson = bson.encode(datos)
        # Escribir el BSON a un archivo
        with open(f"bsons/{file}.bson", "wb") as archivo:
            archivo.write(datos_bson)
        del datos_bson

        if upload_mongo:
            cE.insert_one(
                {
                    "file": f"{file}//{current_hash}",
                    "expYears": expYears,
                    "expYearsManagement": expYearsManagement,
                    "avgTimeInJob": avgTimeInJob,
                    "highestEducation": embedded_edu["maxEducationLevel"],
                    "work": embedded_work,
                    "certification": embedded_cert,
                    "bachelor": (
                        embedded_edu["bachelor"] if "bachelor" in embedded_edu else None
                    ),
                    "maxEducation": (
                        embedded_edu["maxEducation"]
                        if "maxEducation" in embedded_edu
                        else None
                    ),
                    "label": path,
                }
            )
            tracker_db.update_one(
                {"hash": current_hash},
                {"$set": {"status": "processed"}},
            )
        print(Fore.GREEN + f"✅ {file} se procesó correctamente. ✅")
        return output
    except Exception as e:
        if e == "Failed to calculate MD5":
            print(Fore.YELLOW + f"⚠️ El archivo {file} ya no se encuentra disponible ⚠️")
        else:
            print(Fore.RED + f"❌ Error al procesar {file} ❌")
            tracker_db.update_one(
                {"hash": current_hash},
                {"$set": {"status": "failed", "error": str(e)}},
            )
# ------------------- End of Process Documents -------------------
# Paso 7: Creamos un loop para ejecutar el paso 6 en forma paralela, para poder procesar todos los documentos
# de manera eficiente.
for directory in unprocessed.keys():
    print(f"\n📁 Empezando a procesar el Foldere{directory}  📁")
    Parallel(n_jobs=config.get("N_JOBS", 2), prefer="threads")(
        delayed(process_cv)(
            f"resumes/{directory}/",
            file,
            verbose_tokens=False,
            upload_mongo=True,
        )
        for file in unprocessed[directory]
    )

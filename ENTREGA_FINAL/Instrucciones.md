> [!NOTE] 
>Para seguir estos pasos, es necesario tener Docker instalado en un sistema operativo con kernel de Linux bajo la arquitectura amd64. Alternativamente, se conseguir el mismo resultado ejecutando manualmente los pasos descritos en el archivo Dockerfile.
# Obtener el tarball del docker de oracle cloud
Lo primero que debemos hacer es obtener el tarball del Docker de Oracle Cloud. Para ello, usa el siguiente comando:
```bash
wget <url>
```
Tomar en consideración que las **URL** proporcionadas a continuación son de un solo uso:

1. https://axv7bnoptjvq.objectstorage.mx-queretaro-1.oci.customer-oci.com/p/L1Fa3imVcXEjLG7wG6frXEftCW62hJ6CKtYQjdQm6OsLdlfh13Qt41LIRx4xTU57/n/axv7bnoptjvq/b/bucket-20240524-1034/o/pisa-parser.tar

2. https://axv7bnoptjvq.objectstorage.mx-queretaro-1.oci.customer-oci.com/p/tJH38FuNYmNf3Te8y1qlopzLs8ROl1xX7KtqzymCX4R8_c6E9JRrKIT5pcxPCMjw/n/axv7bnoptjvq/b/bucket-20240524-1034/o/pisa-parser.tar

3. https://axv7bnoptjvq.objectstorage.mx-queretaro-1.oci.customer-oci.com/p/X1r9137op1CupjPrNx60etNb09_dasAUFwkAxXCItXC97urC_Zuo-dPaR98DlIbC/n/axv7bnoptjvq/b/bucket-20240524-1034/o/pisa-parser.tar

Para cargar el tarball en Docker, ejecuta el siguiente comando:

> [!NOTE]
> Este comando puede tardar un poco en ejecutarse, ya que el tarball pesa aproximadamente 8GB 🥶

```bash
sudo docker load -i pisa-parser.tar
```

Ahora que tenemos el Docker cargado, podemos ejecutarlo con el siguiente comando:

```bash
sudo docker run -it resume-parser-pisa
```

Una vez ejecutado el comando anterior, se mostrará una pantalla similar a la siguiente:

```bash
root@<container_id>:/resumeparser#
```

A continuación, debemos descargar los CVs que queremos analizar y colocarlos dentro de la carpeta **/resumes/** del contenedor. Para ello, usa el siguiente comando:

```bash
cd resumes/
wget <url>
```

Donde **<url>** es la dirección del comprimido de los CV's que se quiere analizar. 
> [!WARINING]
> Los CVs además de tener ques estar dentro de **/resumes/** también deberán de estar dentro de una subcarpeta que se usará como etiqueta para la clasificación de los CVs.    
Al listar los archivos de la carpeta **/resumes/**, debería mostrarse algo similar a lo siguiente:

```bash
root@<container_id>:/resumeparser/resumes# ls
'Nivel Director'  'Nivel Especialista'  'Nivel Gerente'
```

Una vez hecho esto ya podremos ejecutar el script de python que se encargará de analizar los CV's y clasificarlos en base a su contenido. Para ello se puede usar el siguiente comando:

```bash
cd ..
python main.py
```

Una vez ejecutado el comando anterior, se mostrará una pantalla similar al siguiente:

```bash
-> Parece que aún no se ha creado el archivo .env,
 por favor ingrese la contraseña para crearlo:
```
Después de ingresar la contraseña, se mostrará una pantalla similar al siguiente:

```bash
        Resume Parser para PISA Equipo
ℹ️ Se han encontrado los siguientes directorios ℹ️
  1. Nivel Especialista  (13 documentos)
  2. Nivel Gerente       (12 documentos)
  3. Nivel Director      (9 documentos)

-> Quieres continuar con estos directorios? [Y/n]:
```
Si la la información mostrada es correcta, se deberá de ingresar **Y** para continuar con el proceso de análisis de los CV's. Una vez hecho esto, se mostrará una pantalla similar al siguiente:

```bash

    ℹ️ Cargando configuración inicial ℹ️
⏳ Esto puede tardar un poco, por favor espere. ⌛
modules.json: 100%|█████████████████████████████████████████████████████████████████████████████████████████████████████████| 229/229 [00:00<00:00, 802kB/s]
README.md: 100%|███████████████████████████████████████████████████████████████████████████████████████████████████████| 71.1k/71.1k [00:00<00:00, 10.1MB/s]
sentence_bert_config.json: 100%|██████████████████████████████████████████████████████████████████████████████████████████| 54.0/54.0 [00:00<00:00, 269kB/s]
/usr/local/lib/python3.10/site-packages/huggingface_hub/file_download.py:1132: FutureWarning: `resume_download` is deprecated and will be removed in version 1.0.0. Downloads always resume when possible. If you want to force a new download, use `force_download=True`.
  warnings.warn(
config.json: 100%|█████████████████████████████████████████████████████████████████████████████████████████████████████| 1.35k/1.35k [00:00<00:00, 6.48MB/s]
configuration.py: 100%|████████████████████████████████████████████████████████████████████████████████████████████████| 7.13k/7.13k [00:00<00:00, 28.6MB/s]
A new version of the following files was downloaded from https://huggingface.co/Alibaba-NLP/new-impl:
- configuration.py
. Make sure to double-check they do not contain any added malicious code. To avoid downloading new versions of the code file, you can pin a revision.
modeling.py: 100%|█████████████████████████████████████████████████████████████████████████████████████████████████████| 57.3k/57.3k [00:00<00:00, 62.2MB/s]
A new version of the following files was downloaded from https://huggingface.co/Alibaba-NLP/new-impl:
- modeling.py
. Make sure to double-check they do not contain any added malicious code. To avoid downloading new versions of the code file, you can pin a revision.
/usr/local/lib/python3.10/site-packages/huggingface_hub/file_download.py:1132: FutureWarning: `resume_download` is deprecated and will be removed in version 1.0.0. Downloads always resume when possible. If you want to force a new download, use `force_download=True`.
  warnings.warn(
model.safetensors: 100%|██████████████████████████████████████████████████████████████████████████████████████████████████| 547M/547M [00:03<00:00, 174MB/s]
tokenizer_config.json: 100%|███████████████████████████████████████████████████████████████████████████████████████████| 1.38k/1.38k [00:00<00:00, 3.21MB/s]
vocab.txt: 100%|█████████████████████████████████████████████████████████████████████████████████████████████████████████| 232k/232k [00:00<00:00, 26.5MB/s]
tokenizer.json: 100%|████████████████████████████████████████████████████████████████████████████████████████████████████| 712k/712k [00:00<00:00, 54.2MB/s]
special_tokens_map.json: 100%|█████████████████████████████████████████████████████████████████████████████████████████████| 695/695 [00:00<00:00, 2.02MB/s]
1_Pooling/config.json: 100%|███████████████████████████████████████████████████████████████████████████████████████████████| 297/297 [00:00<00:00, 1.20MB/s]

    ℹ️ Configurando tracker en MongoDB ℹ️
⏳ Esto puede tardar un poco, por favor espere. ⌛

📁 Empezando a procesar el FoldereNivel Especialista  📁
Using Azure OCR.
✅ osiris.pdf se procesó correctamente. ✅
```
Y así sucesivamente hasta que se hayan procesado todos los CV's. 
Sabremos que el proceso ha terminado cuando volvamos a ver el input de la terminal.

```bash
root@<container_id>:/resumeparser#
```

Finalmente los archivos con los datos en texto plano para control se encontrará en la carpeta **/bsons/** del contenedor. 


import os.path
import subprocess
import tempfile
from re import sub

from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from dateutil.parser import parse as dateParse
from docx import Document as Docx
from dotenv import dotenv_values
from magic import from_file

# sudo apt install libreoffice
from unstructured.partition.doc import partition_doc
from unstructured.partition.docx import partition_docx
from unstructured.partition.pdf import partition_pdf


class Extractor:
    CURRENT_ENV: str
    doc_client: DocumentAnalysisClient

    def __init__(self, overwrite_env: str = None) -> None:
        """
        Initializes the Extractor class.

        Args:
            overwrite_env (str): The environment to use. If provided, it will overwrite the environment specified in the .env file.
        Raises:
            Exception: If the .env file is not configured properly.
        """
        config = dotenv_values(".env")

        # If the environment is overwritten, use the environment provided
        if overwrite_env:
            if overwrite_env not in ["dev", "prod"]:
                raise Exception(
                    "El entorno especificado no es válido. Por favor, especifique 'dev' o 'prod'"
                )
            self.CURRENT_ENV = overwrite_env
        else:
            self.CURRENT_ENV = config.get("CURRENT_ENV", "dev")

        # Get the proper Azure credentials
        try:
            if self.CURRENT_ENV == "dev":
                self.doc_client = DocumentAnalysisClient(
                    endpoint=config["AZURE_TEST_OCR_ENDPOINT"],
                    credential=AzureKeyCredential(config["AZURE_TEST_OCR_KEY"]),
                )

            elif self.CURRENT_ENV == "prod":
                self.doc_client = DocumentAnalysisClient(
                    endpoint=config["AZURE_OCR_ENDPOINT"],
                    credential=AzureKeyCredential(config["AZURE_OCR_KEY"]),
                )

        except KeyError:
            raise Exception("Por favor, configura el archivo .env")

    def extract_pdf(
        self, path: str, azure: bool = True, dont_use_other_strategies: bool = False
    ) -> str:
        """
        Extracts the text from a PDF file. It tries to extract the text contained in the PDF naively,
        if no text is found, it uses the OCR to extract the text.

        Args:
            path (str): The path to the PDF file.
            azure (bool, optional): Flag indicating whether to use Azure Document Intelligence service. Defaults to True.
            dont_use_other_strategies (bool, optional): Flag indicating whether to use other strategies to extract the text. Defaults to False.

        Returns:
            str: The extracted text from the PDF file.
        """
        elements = partition_pdf(path, strategy="fast", languages=["eng", "spa"])

        if len(elements) <= 3:  # If the text is not found, use OCR
            if dont_use_other_strategies:
                return "Not enough elements found"

            elif azure:
                print("Using Azure OCR.")
                with open(path, "rb") as pdf:
                    poller = self.doc_client.begin_analyze_document(
                        "prebuilt-read", pdf, locale="es"
                    )
                    result = poller.result()
                    return result.content
            else:
                elements = partition_pdf(
                    path,
                    strategy="hi_res",
                    languages=["eng", "spa"],
                    pdf_infer_table_structure=True,
                )

        allText = "\n".join([element.text for element in elements])
        return sub(r"\n+", "\n", allText)

    def extract_word_doc(
        self, path: str, azure: bool = True, include_metadata: bool = False
    ) -> str:
        """
        Extracts the text from a .doc file, if no text is found, it uses the OCR to extract the text.

        Args:
            path (str): The path to the .doc file.
            azure (bool, optional): Flag indicating whether to use Azure Document Intelligence service. Defaults to True.
            include_metadata (bool, optional): Flag indicating whether to include the metadata in the extraction. Defaults to True.

        Returns:
            str: The extracted text from the .doc file.
        """
        elements = partition_doc(
            path, languages=["eng", "spa"], include_metadata=include_metadata
        )

        if len(elements) <= 3:  # If the text is not found, use OCR
            if azure:
                print("Using Azure OCR.")
                with open(path, "rb") as doc:
                    poller = self.doc_client.begin_analyze_document(
                        "prebuilt-read", doc, locale="es"
                    )
                    result = poller.result()
                    return result.content

        allText = "\n".join([element.text for element in elements])
        if include_metadata:
            if elements[-1].metadata.last_modified:
                return (
                    allText,
                    dateParse(elements[-1].metadata.last_modified).timestamp(),
                )
        return sub(r"\n+", "\n", allText)

    def convert_docx_to_pdf_and_extract_text(self, input_file, azure=True):
        # Ensure LibreOffice is installed and accessible from the command line
        try:
            subprocess.run(["libreoffice", "--version"], check=True)
        except subprocess.CalledProcessError:
            print(
                "LibreOffice is not installed or not accessible from the command line."
            )
            return "Not enough elements found"

        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Construct the command to convert the DOCX to PDF
            command = [
                "libreoffice",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                temp_dir,
                input_file,
            ]

            # Run the command
            try:
                subprocess.run(command, check=True)
                # Get the name of the PDF file
                pdf_file = os.path.join(
                    temp_dir, os.path.splitext(os.path.basename(input_file))[0] + ".pdf"
                )

                # Extract text from the PDF file
                text = self.extract_pdf(pdf_file, azure, dont_use_other_strategies=True)
                return text

            except subprocess.CalledProcessError as e:
                print(
                    f"An error occurred while converting {input_file} to PDF: {str(e)}"
                )
                return "Not enough elements found"

    def extract_word_docx(self, path: str, azure: bool = True) -> str:
        """
        Extracts the text from a .docx file, if no text is found, it uses the OCR to extract the text.

        Args:
            path (str): The path to the .docx file.
            azure (bool, optional): Flag indicating whether to use Azure Document Intelligence service. Defaults to True.

        Returns:
            str: The extracted text from the .docx file.
        """
        elements = partition_docx(path, languages=["eng", "spa"])

        if len(elements) <= 3:  # If the text is not found, use OCR
            allText = self.convert_docx_to_pdf_and_extract_text(path, azure)
            if azure and allText == "Not enough elements found":
                print("Using Azure OCR.")
                with open(path, "rb") as docx:
                    poller = self.doc_client.begin_analyze_document(
                        "prebuilt-read", docx, locale="es"
                    )
                    result = poller.result()
                    return result.content
            return allText

        allText = "\n".join([element.text for element in elements])
        return sub(r"\n+", "\n", allText)

    def extract(
        self, path: str, azure: bool = True, return_created_at: bool = False
    ) -> str:
        """
        Extracts the text from a file based on the mimetype of the file.

        Args:
            path (str): The path to the file.
            azure (bool, optional): Flag indicating whether to use Azure Document Intelligence service. Defaults to True.
            return_created_at (bool, optional): Flag indicating whether to return the creation date of the file. Defaults to False.

        Returns:
            str: The extracted text from the file.
        """
        file_type = from_file(path, mime=True)
        # PDF files
        if file_type == "application/pdf" and path.lower().endswith(".pdf"):
            if return_created_at:
                return os.path.getctime(path), self.extract_pdf(path, azure)
            return self.extract_pdf(path, azure)

        # Word .docx files
        elif (
            file_type
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ) and path.lower().endswith(".docx"):
            if return_created_at:
                modified = Docx(path).core_properties.modified.timestamp()
                return modified, self.extract_word_docx(path, azure)
            return self.extract_word_docx(path, azure)

        # Word .doc files
        elif file_type == "application/msword" and path.lower().endswith(".doc"):
            if return_created_at:
                allText, modified = self.extract_word_doc(
                    path, azure, include_metadata=True
                )
                return modified, allText
            return self.extract_word_doc(path, azure)

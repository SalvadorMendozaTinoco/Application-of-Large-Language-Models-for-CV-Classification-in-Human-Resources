from datetime import datetime, timedelta
from math import ceil
from re import compile

from dateutil.parser import parse as dateParse
from intervaltree import Interval, IntervalTree
from langchain_community.embeddings import HuggingFaceEmbeddings

regexPattern = compile(
    r"Type:\W*(?P<type>.*)(\WManagement:\W*(?P<management>.*))?\WTitle:\W*(?P<title>.*)\WInstitution:\W*(?P<institution>.*)\WStart Date:\W*(?P<start>.*)(\WEnd Date:\W*(?P<end>.*))?\W(Brief:\W*(?P<brief>.*))?"
)

from datetime import datetime, timedelta


def strip_and_NA(field_content: str) -> str:
    """
    Strips the string and standarizes None like values to NA.

    Args:
        field_content (str): The string to strip.

    Returns:
        str: The stripped string or 'NA' if the string is empty.
    """
    if field_content is None:
        return "NA"
    field_content = field_content.strip()
    if (
        "n/a" in field_content.lower()
        or field_content == ""
        or field_content.lower() == "n"
        or "none" in field_content.lower()
    ):
        return "NA"
    return field_content


def education_labeler(education: str) -> int:
    """
    Assigns a label to the given education level.

    Parameters:
    education (str): The education level to be labeled.

    Returns:
    int: The label assigned to the education level.
    """

    if "bachelor" in education.lower():
        return 1
    if ("mba" in education.lower()) or ("master" in education.lower()):
        return 2
    if (
        ("engineer" in education.lower())
        or ("licenciatura" in education.lower())
        or ("intern" in education.lower())
    ):
        return 1
    if (
        ("doctor" in education.lower())
        or ("phd" in education.lower())
        or ("ph.d" in education.lower())
    ):
        return 3
    if ("high school" in education.lower()) or ("bachiller" in education.lower()):
        return 0
    return -1


def apply_regex_template(outs: str, createdAt: float):
    """
    Applies the regex template to the extracted text and categorizes the matches into work experience, education, and certification.

    This function iterates over the matches found in 'outs', processes each match,
    and categorizes them into work experience, education, and certification.

    Parameters:
    outs (str): The string to find matches in.
    createdAt (float): The Unix timestamp representing the creation time.

    Returns:
    list: A sorted list of dictionaries representing the work experience.
    list: A list of dictionaries representing the education.
    list: A list of dictionaries representing the certification.
    """
    work, education, certification = [], [], []
    for match in regexPattern.finditer(outs):
        try:
            match = match.groupdict()
            # We check the presence of End Date inside of Start as it's a problematic field
            # As commonly the LLM does not add an \n after the start date
            if "End Date:" in match["start"]:
                match["start"], match["end"] = match["start"].split("End Date:")

            match = {k: strip_and_NA(v) for k, v in match.items()}
            if (match["start"] != "NA") and (match["start"] != "Present"):
                match["start"] = dateParse(
                    match["start"],
                    default=datetime(1, 1, 1),
                    fuzzy=True,
                    fuzzy_with_tokens=True,
                )
                # We check the presence of the word "present" in the start date
                # as often the LLM confuses and omits the end date in the case of present
                if any("present" in token.lower() for token in match["start"][1]):
                    match["end"] = "Present"
                match["start"] = match["start"][0]

            if (match["end"] != "NA") and (match["end"] != "Present"):
                match["end"] = dateParse(
                    match["end"], default=datetime(1, 1, 1), fuzzy=True
                )

            if "work experience" in match["type"].lower():
                if (match["end"] == "NA") and (match["start"] == "NA"):
                    match["start"], match["end"] = datetime(1969, 12, 31, 18), datetime(
                        1970, 1, 1, 18
                    )
                elif match["end"] == "NA":
                    # If we don't have an end date, we assume it's 3 months after the start date
                    match["end"] = match["start"] + timedelta(days=90)
                    match["fictional"] = True

                elif match["end"] == "Present":
                    match["end"] = datetime.fromtimestamp(createdAt).replace(
                        day=1, hour=0, minute=0, second=0, microsecond=0
                    )
                work.append(match)

            elif "education" in match["type"].lower():
                match.pop("management", None)
                match["education_level"] = education_labeler(match["title"])
                education.append(match)

            elif "certification" in match["type"].lower():
                match.pop("management", None)
                certification.append(match)
        except:
            print("Error while parsing", match)

    if len(work) > 0:
        work.sort(key=lambda x: x["end"] if x["end"] != "NA" else x["start"])

    return work, education, certification


def aggregate_work_experience(work: list, only_management: bool = False) -> float:
    """
    Calculate the total work experience in years based on a list of work intervals.

    Args:
        work (list): A list of dictionaries representing work intervals. Each dictionary should have "start" and "end" keys, which are datetime objects representing the start and end dates of the work interval.
        only_management (bool, optional): Flag indicating whether to consider only management positions. Defaults to False.

    Returns:
        float: The total work experience in years.

    """
    if len(work) == 0:
        return 0
    starting_pos = 0
    tree = IntervalTree()
    for w in work:
        # If we just want to aggregate management positions, we skip the rest
        if only_management and w["management"] == "No":
            continue

        if starting_pos == 0:
            if w["start"].timestamp() != 0.0:
                starting_pos = ceil(w["start"].timestamp() / 86400)
                tree.add(
                    Interval(
                        ceil(w["start"].timestamp() / 86400) - starting_pos,
                        ceil(w["end"].timestamp() / 86400) - starting_pos + 1,
                    )
                )
        else:
            tree.add(
                Interval(
                    ceil(w["start"].timestamp() / 86400) - starting_pos,
                    ceil(w["end"].timestamp() / 86400) - starting_pos + 1,
                )
            )
    if len(tree) == 0:
        return 0
    tree.merge_overlaps()
    return sum(interval.length() for interval in tree) / 365


def avg_time_in_job(work: list) -> float:
    """
    Calculate the average time spent in a job based on a list of work intervals.

    Args:
        work (list): A list of dictionaries representing work intervals. Each dictionary should have "start" and "end" keys, which are datetime objects representing the start and end dates of the work interval.

    Returns:
        float: The average time spent in a job in years.

    """
    if len(work) == 0:
        return 0
    durations = []
    for w in work:
        # If the work experience is fictional, we don't consider it
        if w.get("fictional", False):
            continue
        durations.append((w["end"] - w["start"]).days)
    return sum(durations) / len(durations) / 365


def extract_resume_features(outs, createdAt):
    """
    Extracts resume features from the given inputs in a human redable form.

    Parameters:
    - outs: The outputs of the resume extraction process.
    - createdAt: The creation timestamp of the resume.

    Returns:
    - work: The extracted work experience information.
    - education: The extracted education information.
    - certification: The extracted certification information.
    - expYears: The aggregated work experience in years.
    - expYearsManagement: The aggregated work experience in years for management roles only.
    - avgTimeInJob: The average time spent in each job.

    """
    work, education, certification = apply_regex_template(outs, createdAt)
    del outs, createdAt
    expYears = aggregate_work_experience(work)
    expYearsManagement = aggregate_work_experience(work, only_management=True)
    avgTimeInJob = avg_time_in_job(work)
    return work, education, certification, expYears, expYearsManagement, avgTimeInJob


def embed_works(works: list, embeddings: HuggingFaceEmbeddings) -> list:
    """
    Embeds the works using the provided HuggingFaceEmbeddings model.

    Args:
        works (list): A list of works to be embedded.
        embeddings (HuggingFaceEmbeddings): The HuggingFaceEmbeddings model used for embedding.

    Returns:
        list: A list of embedded works, where each work is represented as a dictionary with the following keys:
            - "title": The embedded vector representation of the work's title.
            - "institution": The embedded vector representation of the work's institution.
            - "brief": The embedded vector representation of the work's brief.
            - "management": An integer indicating whether the work has management (1) or not (0).
            - "work_counter": The count of works encountered so far.
    """

    if len(works) == 0:
        return []
    embedded_work = []
    work_counter = -1
    for w in works:
        if w["start"] != datetime(1969, 12, 31, 18):
            work_counter += 1
        vectors = embeddings.embed_documents([w["title"], w["institution"], w["brief"]])
        embedded_work.append(
            {
                "title": vectors[0],
                "institution": vectors[1],
                "brief": vectors[2],
                "management": 0 if w["management"] == "No" else 1,
                "work_counter": work_counter,
            }
        )
    return embedded_work


def embed_certifications(
    certifications: list, embeddings: HuggingFaceEmbeddings
) -> list:
    """
    Embeds the given list of certifications using the provided HuggingFaceEmbeddings object.

    Args:
        certifications (list): A list of dictionaries representing certifications. Each dictionary should have a "title" and "brief" key.
        embeddings (HuggingFaceEmbeddings): An instance of the HuggingFaceEmbeddings class used for embedding the certifications.

    Returns:
        list: A list of dictionaries representing the embedded certifications. Each dictionary will have a "title" and "brief" key, with their respective embeddings.
    """
    if len(certifications) == 0:
        return []
    embedded_certification = []
    for w in certifications:
        vectors = embeddings.embed_documents([w["title"], w["brief"]])
        embedded_certification.append({"title": vectors[0], "brief": vectors[1]})
    return embedded_certification


def embed_education(education: list, embeddings: HuggingFaceEmbeddings) -> dict:
    """
    Embeds education information using HuggingFace embeddings.
    The dictionary will contain following keys:
    - maxEducationLevel: The highest education level reached.
    - bachelor (If possible): A dictionary containing the embedded vector representation of the bachelor's title and institution.
    - maxEducation (If possible): A dictionary containing the embedded vector representation of the highest education level reached title and institution.

    Args:
        education (list): A list of dictionaries containing education information.
        embeddings (HuggingFaceEmbeddings): An instance of the HuggingFaceEmbeddings class.

    Returns:
        dict: A dictionary containing the embedded education information.

    """
    if len(education) == 0:
        return {"maxEducationLevel": -1}

    # We just want to keep Bachelors information and the highest degree reached
    maxEducationLevel, mIdx = -1, -1  # mIdx stands for maxEducation index
    bIdx = -1  # bIdx stands for bachelor index
    for idx, edu in enumerate(education):
        if edu["education_level"] > maxEducationLevel:
            maxEducationLevel = edu["education_level"]
            mIdx = idx
        if edu["education_level"] == 1:
            bIdx = idx

    # We create a list to embed all features in the same batch
    toEmbed = []
    if maxEducationLevel > 0:
        toEmbed.append(education[bIdx]["title"])
        toEmbed.append(education[bIdx]["institution"])
        if maxEducationLevel != 1:
            toEmbed.append(education[mIdx]["title"])
            toEmbed.append(education[mIdx]["institution"])
    vectors = embeddings.embed_documents(toEmbed)

    # Construct response
    embedded_education = {"maxEducationLevel": maxEducationLevel}
    if maxEducationLevel > 0:
        embedded_education["bachelor"] = {
            "title": vectors[0],
            "institution": vectors[1],
        }
        if maxEducationLevel != 1:
            embedded_education["maxEducation"] = {
                "title": vectors[2],
                "institution": vectors[3],
            }
    return embedded_education

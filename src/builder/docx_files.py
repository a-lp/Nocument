from io import BytesIO
import zipfile

TEMPLATE_CONTENT_TYPE = b"application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml"
DOCUMENT_CONTENT_TYPE = b"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"


def template_to_document(content: bytes) -> bytes:
    """
    Converts a Word template (.dotx) into a document (.docx): only changes the type of the main part in
    [Content_Types].xml, because python-docx only opens documents.
    """
    source = zipfile.ZipFile(BytesIO(content))
    output = BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as target:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename == "[Content_Types].xml":
                data = data.replace(TEMPLATE_CONTENT_TYPE, DOCUMENT_CONTENT_TYPE)
            target.writestr(item, data)
    return output.getvalue()

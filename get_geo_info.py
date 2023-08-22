import requests
from xml.etree import ElementTree

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

def fetch_gsm_details(gsm_id):
    url = f"{BASE_URL}esearch.fcgi?db=gds&term={gsm_id}[ACCN]&retmax=1"
    response = requests.get(url)
    root = ElementTree.fromstring(response.content)
    gds_id = root.find("IdList/Id").text
    return gds_id

def fetch_downloadables(gds_id):
    url = f"{BASE_URL}efetch.fcgi?db=gds&id={gds_id}"
    response = requests.get(url)
    content = response.content.decode('utf-8')
    
    # Check if the response is in XML format
    if content.strip().startswith('<'):
        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError:
            print("Error parsing XML. Response content:")
            print(content)
            return []

        downloadables = []
        for item in root.findall(".//Item[@Name='download']"):
            description = item.find(".//Item[@Name='description']").text
            file_type = item.find(".//Item[@Name='filetype']").text
            file_url = item.find(".//Item[@Name='url']").text
            downloadables.append({
                "description": description,
                "file_type": file_type,
                "file_url": file_url
            })
        return downloadables
    else:
        # Extract FTP download link from plain text
        for line in content.splitlines():
            if "FTP download:" in line:
                ftp_link = line.split()[-1]
                return [{"description": "FTP Download Link", "file_type": "FTP", "file_url": ftp_link}]
        return []

def main():
    gsm_id = input("Enter the GSM number: ")
    gds_id = fetch_gsm_details(gsm_id)
    downloadables = fetch_downloadables(gds_id)
    
    for item in downloadables:
        print(f"Description: {item['description']}")
        print(f"File Type: {item['file_type']}")
        print(f"URL: {item['file_url']}")
        print("-" * 50)

if __name__ == "__main__":
    main()

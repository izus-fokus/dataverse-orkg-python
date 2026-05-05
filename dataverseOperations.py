import requests

class DataverseOperations:

    def __init__(self, dataverseUrl) -> None:
        # self.header = header
        self.dataverseUrl = dataverseUrl

    def get_dataset(self, pid):
        jsonDataset = requests.get("https://" + self.dataverseUrl + "/api/datasets/:persistentId/?persistentId=" + pid,
                                   ).json()
        return jsonDataset



def getWorkspaceRequestorPays(bucketName):
    result = !gsutil -u anvil-datastorage requesterpays get  gs://$bucketName
    return ( "Enabled" in result[0])

def getWorkspaceBucketSize(bucketName):
    result = !gsutil -u anvil-datastorage du -s gs://$bucketName
    return result[0].split()[0]
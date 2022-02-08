from functions import file_handler

class WebsiteMeta:
    if (b:=file_handler("creds.txt")) :
            b = b.split("\n")
            username, password, api_key , public_context, testing_chat_context = b
    else:
        raise FileNotFoundError("Please write the necessary credentials")
    blacklist = {}
        
import os
import shutil
import logging
from typing import List
from O365 import Account, FileSystemTokenBackend
from searchflow.models.documents import FileObject

class OneDrive:
    '''
    Connect to a OneDrive account and index files.
    '''
    def __init__(self, azure_client_id : str, azure_client_secret: str) -> None:
        self.logger = logging.getLogger(__name__)

        if not azure_client_id or not azure_client_secret:
            self.logger.error("Azure client id and secret are required.")

        self.token_backend = FileSystemTokenBackend(token_path='.', token_filename='o365_token.txt')
        self.account = Account(credentials=(azure_client_id, azure_client_secret), token_backend=self.token_backend)
        self.local_dir = None

        # Authenticate the account
        if not self.account.is_authenticated:
            if self.account.authenticate(scopes=['onedrive_all']):
                self.logger.info("Authenticated successfully.")
            else:
                self.logger.error("Authentication failed.")

    def list_files(self, folder_path : str = '/') -> List[dict]:
        '''
        Lists the files in a OneDrive folder.
        '''

        # Get the storage object for the OneDrive
        storage = self.account.storage()

        # Get the default drive (main OneDrive)
        drive = storage.get_default_drive()

        files = []

        if drive:
            # Get the specified folder
            if folder_path == '/':
                folder = drive.get_root_folder()
            else:
                folder = drive.get_item_by_path(folder_path)

            try:
                items = folder.get_items()
                for item in items:
                    item_type = 'File' if item.is_file else 'Folder'
                    files.append({'name': item.name, 'type': item_type})

            except Exception as e:
                self.logger.error("Failed to get items in the folder: %s", e)
        else:
            self.logger.error("Failed to get the default drive.")
            return []
        return files
    
    def download_files(self, folder_path: str = '/', exts: List[str] = []) -> List[FileObject] | None:
        """
        Downloads files from a specified OneDrive folder.

        This function connects to the user's OneDrive account, navigates to the specified folder,
        and downloads files with the given extensions. The downloaded files are saved in a local
        directory named after the OneDrive folder's drive ID.

        Args:
            folder_path (str, optional): The path to the OneDrive folder from which to download files.
                Defaults to '/' (root folder).
            exts (List[str], optional): A list of file extensions to filter the files for download.
                If empty, all files will be considered for download. Defaults to an empty list.

        Returns:
            A list of FileObject instances representing the downloaded files.

        Raises:
            No specific exceptions are raised, but errors are logged using self.logger.

        Note:
            - The function creates a local directory './temp/{drive_id}' to store the downloaded files.
            - If a file fails to download, an error is logged, and the function continues with the next file.
            - If the default drive cannot be accessed, an error is logged, and the function returns.
        """
        # Get the storage object for the OneDrive
        try:
            storage = self.account.storage()
        except Exception as e:
            self.logger.error("Failed to get storage object, please iniitialize the class: %s", e)
            return None

        # Get the default drive (main OneDrive)
        drive = storage.get_default_drive()

        if drive:
            # Get the specified folder
            if folder_path == '/':
                folder = drive.get_root_folder()
            else:
                folder = drive.get_item_by_path(folder_path)

            # Get the items in the folder
            items = folder.get_items()

            download_count = 0

            exts = [ext.lower() for ext in exts]
            
            # Create a folder with the sane name as the OneDrive folder
            drive_id = folder.drive_id
            self.local_dir = f"./temp/{drive_id}"

            if self.local_dir and os.path.exists(self.local_dir):
                shutil.rmtree(self.local_dir)

            os.makedirs(self.local_dir)

            file_objects = []

            for item in items:
                if item.is_file:
                    if not exts or str(item.extension).lower() in exts:
                        # Download the file
                        try:
                            logging.info("Downloading file: %s", item.name)
                            item.download(to_path=self.local_dir)
                            download_count += 1
                            file_objects.append(FileObject(
                                file_path=f"{self.local_dir}/{item.name}",
                                file_type=item.extension,
                                file_name=item.name,
                                url=item.web_url
                            ))
                        except Exception as e:
                            self.logger.error("Failed to download file: %s", e)
                            continue
        else:
            self.logger.error("Failed to get the default drive.")
            return
        
        return file_objects
    
    def close(self):
        '''
        Removes the downloded files from the local directory.
        Closes the connection to the OneDrive account.
        '''
        # Remove the downloaded files (if any)
        if self.local_dir and os.path.exists(self.local_dir):
            shutil.rmtree(self.local_dir)

        self.token_backend = None
        self.account = None
        self.local_dir = None




import os
import requests

class AudioUtils:
    ALLOWED_EXTENSIONS = {'mp4', 'mp3', 'wav', 'ogg'}

    @staticmethod
    def extract_time(url):
        """
        Extracts the time from a URL.

        Args:
            url (str): The URL containing the time information.

        Returns:
            str: The extracted time in format 'HH-MM-SS'.
        """
        time_segment = url.split("TIME-")[-1]  # Get the segment after "TIME-"
        return '-'.join(time_segment.split('-')[:3])  # Join the first three parts

    @staticmethod
    def replace_characters(string, to_be_replaced, replacing):
        """
        Replaces characters in a string.

        Args:
            string (str): The original string.
            to_be_replaced (str): The character(s) to be replaced.
            replacing (str): The replacement character(s).

        Returns:
            str: The modified string.
        """
        return string.replace(to_be_replaced, replacing)

    @staticmethod
    def convert_to_hms(partition, slice, seconds):
        """
        Converts seconds to hours, minutes, and seconds format.

        Args:
            partition (int): The partition number.
            slice (int): The slice number.
            seconds (int): The number of seconds.

        Returns:
            str: The time in HH:MM:SS format.
        """
        total_seconds = (partition * 12 + slice * 3) * 60 + seconds
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @staticmethod
    def download_file(url, save_path):
        """
        Downloads a file from a URL to the specified save path.

        Args:
            url (str): The URL of the file to download.
            save_path (str): The path where the file will be saved.
        """
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an error for bad responses
            with open(save_path, 'wb') as file:
                file.write(response.content)
            print("File downloaded successfully")
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while downloading: {e}")

    @staticmethod
    def allowed_file(filename):
        """
        Checks if the file has an allowed extension.

        Args:
            filename (str): The name of the file.

        Returns:
            bool: True if the file has an allowed extension, False otherwise.
        """
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in AudioUtils.ALLOWED_EXTENSIONS

    @staticmethod
    def setup_upload_folder(folder_name='temp'):
        """
        Sets up the upload folder if it doesn't exist.

        Args:
            folder_name (str): The name of the upload folder.
        """
        upload_folder = os.path.join(os.getcwd(), folder_name)
        os.makedirs(upload_folder, exist_ok=True)
        return upload_folder

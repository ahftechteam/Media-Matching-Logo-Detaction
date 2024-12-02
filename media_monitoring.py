from datetime import datetime
import os
import numpy as np
import soundfile as sf
import ffmpeg
import librosa
import subprocess
import shutil
from models.fingerprints import Fingerprint
from database.database import db

class AudioFingerprintGenerator:
    @staticmethod
    def get_file_duration(file_path):
        try:
            probe = ffmpeg.probe(file_path)
            duration = float(probe['format']['duration'])
            return duration
        except Exception as e:
            return None

    @staticmethod
    def convert_video_to_audio(base_dir, mp4_file):
        try:
            wav_file = os.path.join(base_dir, 'audio.wav')
            duration = str(AudioFingerprintGenerator.get_file_duration(mp4_file))
            print("duration", duration)

            command = [
                'ffmpeg',
                '-i', mp4_file,
                "-async", "1",
                wav_file
            ]
            subprocess.run(command, check=True)

            print("Conversion done")
            print("duration", AudioFingerprintGenerator.get_file_duration(wav_file) )
            return wav_file
        except Exception as e:
            return e

    @staticmethod
    def initialize_fingerprinting_folders():
        try:
            for folder in ['radio', 'tv', 'temp']:
                folder_path = os.path.join(os.getcwd(), folder)
                os.makedirs(folder_path, exist_ok=True)
        except Exception as e:
            return e

    @staticmethod
    def clear_temporary_folder(folder_path):
        try:
            shutil.rmtree(folder_path)
        except Exception as e:
            return e



    def partition_large_audio(self, file_path, minute, base_dir):
        try:
            partitioned_large_audio_files_size = 0
            os.makedirs(base_dir, exist_ok=True)
            
            file_extension = file_path.split('.')[-1]
            if file_extension == 'mp4':
                file_path = self.convert_video_to_audio(base_dir, file_path)
            
            wave, sr = librosa.load(file_path, sr=None)
            segment_dur_secs = minute * 60 
            total_duration_secs = len(wave) / sr
            num_sections = int(np.ceil(total_duration_secs / segment_dur_secs))
            split = [wave[i * segment_dur_secs * sr: (i + 1) * segment_dur_secs * sr] for i in range(num_sections)]

            print('has reached this section')
            for i, section in enumerate(split):
                out_file = f"partition_{i}.wav"  
                sf.write(os.path.join(base_dir, out_file), section, sr)

                partitioned_large_audio_files_size += 1

        
            return [0] * partitioned_large_audio_files_size

        except Exception as e:
            return e

    def slice_to_smaller_piece(self, base_dir, partition_index, slice_destination_folder, slice_duration_minutes):  
        try:
            os.makedirs(slice_destination_folder, exist_ok=True)
            audio_file_path = os.path.join(base_dir, f'partition_{partition_index}.wav')
            wave, sr = librosa.load(audio_file_path, sr=None)

            slice_duration_secs = slice_duration_minutes * 60
            slice_length = sr * slice_duration_secs
            num_slices = int(np.ceil(len(wave) / slice_length))

            slices = [wave[i * slice_length: (i + 1) * slice_length] for i in range(num_slices)]

            for i, slice in enumerate(slices):
                sf.write(os.path.join(slice_destination_folder, f"slice_{i}.wav"), slice, sr)
            
            return num_slices
            
        except Exception as e:
            return e


    def generate_fingerprint(self, partition_index, num_slices, slice_audio_path, fingerprint_destination_path):

        try:
            os.makedirs(fingerprint_destination_path, exist_ok=True)
            num_fingerprints = 0
            dbase_path = f"{fingerprint_destination_path}/partition_{partition_index}.pklz"

            for i in range(num_slices):
                slice_path = f"{slice_audio_path}/slice_{i}.wav"
                
                if i == 0:
                    command = f"python3 audfprint.py new --dbase {dbase_path} {slice_path} --density 100 --samplerate 11025 --shifts 4"
                else:
                    command = f"python3 audfprint.py add --dbase {dbase_path} {slice_path} --density 100 --samplerate 11025 --shifts 4"
                
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                    
                # Check the return code
                if result.returncode == 0:
                    print("Command executed successfully:")
                    num_fingerprints += 1
                else:
                    print("Command failed with return code:", result.returncode)
                    print("Error message:", result.stderr)  # Error output from the command
            
            return num_fingerprints == num_slices
        
        except Exception as e:
            return e


    @staticmethod
    def search_for_matching(fingerprint_database_path, num_partitions, advert_file_path):
        try:
            file_extension = advert_file_path.split('.')[-1]
            if file_extension == 'mp4':
                # base_dir = advert_file_path.split('/')[:-1].join('/') 
                base_dir = '/'.join(advert_file_path.split('/')[:-1])
                print('base_dir', base_dir, advert_file_path)
                advert_file_path = AudioFingerprintGenerator.convert_video_to_audio(base_dir, advert_file_path)

            total_matches = []

            for idx in range(num_partitions):
                dbase_path = f"{fingerprint_database_path}/partition_{idx}.pklz"
                command = f"python3 audfprint.py match --dbase {dbase_path} {advert_file_path} --density 100 --samplerate 11025 --match-win 60 --min-count 200 --max-matches 50 --find-time-range"
                output = subprocess.run(command, capture_output=True, text=True, shell=True)
                txt = output.stdout
                lines = txt.split('\n')
                
                for line in lines:
                    print(line)
                    if line.startswith('Matched'):
                        parts = line.split()
                        matched_file_path = parts[14]
                        print('parts:', parts)
                        partition_number = matched_file_path.split('/')[-2].split('_')[-1]
                        slice_number = matched_file_path.split('/')[-1].split('_')[-1].split('.')[0]
                        # starting_time_str = parts[10]  

                        # starting_time = float(starting_time_str)

                        # if starting_time < 0:
                        #     total_duration = float(parts[2])  
                        #     starting_time = total_duration + starting_time

                        # print("Starting time (in seconds):", starting_time)
                        seconds = parts[11]
                        total_matches.append((partition_number, slice_number, seconds))

                print("Total matches: ", total_matches)
            return total_matches
        
        except Exception as e:
            return e


    def initiate_fingerprinting(self, recording_id, file_path, partition_duration_minutes, slice_duration_minutes, fingerprint_destination_path):
        try:
            base_dir = os.path.join(os.getcwd(), 'temp', recording_id)
            os.makedirs(base_dir, exist_ok=True)
            partitioned_audio_files = self.partition_large_audio(file_path, partition_duration_minutes, base_dir)
            total_duration = 0

            for partition_index in range(len(partitioned_audio_files)):
                slice_destination_folder = f"{base_dir}/partition_{partition_index}"
                num_slices = self.slice_to_smaller_piece(base_dir, partition_index, slice_destination_folder, slice_duration_minutes)
                partitioned_audio_files[partition_index] = num_slices

                duration_secs = num_slices * slice_duration_minutes * 60
                total_duration += duration_secs

            for partition_index, num_slices in enumerate(partitioned_audio_files):
                slice_audio_path = os.path.join(base_dir, f"partition_{partition_index}")
                self.generate_fingerprint(partition_index, num_slices, slice_audio_path, fingerprint_destination_path)

            fingerprint = Fingerprint.create(recording_id, fingerprint_destination_path, len(partitioned_audio_files), total_duration, datetime.now())
            fingerprint_dict = fingerprint.to_dict()
            return fingerprint_dict 

        except Exception as e:
            return e

class MediaMonitoring:

    def __init__(self):
        AudioFingerprintGenerator.initialize_fingerprinting_folders()

    def make_fingerprint(self, recording_id, file_path, partition_duration_minutes, slice_duration_minutes, fingerprint_destination_path):
        try:
            generator = AudioFingerprintGenerator()
            fingerprint = generator.initiate_fingerprinting(recording_id, file_path, partition_duration_minutes, slice_duration_minutes, fingerprint_destination_path)
            temp_folder = os.path.join(os.getcwd(), 'temp')
            AudioFingerprintGenerator.clear_temporary_folder(os.path.join(os.getcwd(),temp_folder))
            return fingerprint
        
        except Exception as e:
            return False

    def make_matching(self, recording_id, advert_file_path):
        try:
            print('advert_file_path',advert_file_path )
            
            fingerprint = Fingerprint.get_by_recording_id(recording_id)
            if fingerprint is None:
                return {"message":"No fingeprint found"}
	           
            fingerprint_database_path = fingerprint.file_path
            num_partitions = fingerprint.num_partitions
            print('matches', fingerprint_database_path)
            
            matches = AudioFingerprintGenerator.search_for_matching(fingerprint_database_path, num_partitions, advert_file_path)
            return matches
        
        except Exception as e:
            return []

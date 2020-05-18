# Photo-organizer

- Personal photo backup project.
- Just verified from my fixed environment.
- Need to cleanup codes


# Feature

 - Merge distributed photo folder/files into one place
 - Photo/Movie will be reorganized by month
````Example)
      2019/2019_01
           2019_02
           ...
      2020/2020_01
           2020_02
           ...
````  
  - Check duplicated photo/movie and skip duplicated photo/movie copy
  - Known extension photo/movie : JPG/MOV/MP4/MTS/HEIC
  
# Usage

    $ ./photo_organizer.py --help
    usage: photo_organizer.py [-h] -s SOURCE -t TARGET [--index_db INDEX_DB]
                          [--logfile LOGFILE]

    optional arguments:
      -h, --help            show this help message and exit
      -s SOURCE, --source SOURCE
                            Source path - Photo From path
      -t TARGET, --target TARGET
                            Target path - Photo Copy to path
      --index_db INDEX_DB   Load index db for target path(skip indexing target path)
      --logfile LOGFILE     logfile for detail progress


# Example	Command

    $ ./photo_organizer.py --source {source_folder} --target {target_folder} --index_db photo.db --logfile log.txt

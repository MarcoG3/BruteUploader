# BruteUploader
Inspired after seeing a lot of bad practices in implementing a file upload mainly in PHP, I coded a quick script to brute-force newly uploaded files in a website. This could be useful in websites that let you upload files and hide the actual file location.

## Usage
`./bruteuploader.py -h`

## Example
`./bruteuploader.py -u http://127.0.0.1/upload.php -f file1 -x http://127.0.0.1/uploads -d 'submit=Submit+Now' -p supersh3ll.php`


[//]: # "TODO: write a real readme"

### instructions:
  
first unzip it
  
#### windows:  
  
make sure to run this on [windows terminal](https://apps.microsoft.com/detail/9n0dx20hk701?)  
cmd/powershell kinda works but is really bad due to lack of support for ANSI codes  
  
#### linux:  
```bash
chmod +x main
./main
```
warning: if it doesn't run just execute source with `python3 src/main.py`
  
#### mac:  
```bash
chmod +x dist/main
xattr -d com.apple.quarantine dist/main
./main
```  
not really sure if xattr is needed because I don't have a mac  

### building it:

```bash
python -m venv .venv
# windows:
.venv\Scripts\activate
# linux or mac:
source .venv/bin/activate
pip install -r requirements.txt
pyinstaller src/main.spec
```
  
#### enjoy :D  

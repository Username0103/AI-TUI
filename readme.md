
[//]: # "TODO: write a real readme or something"

### what it does:

this is a terminal based application for talking with llms.  
it supports extensible configuration, is user-friendly, undo/redo, etc.  

### instructions to run with pip:

see [this](https://pypi.org/project/AI-Terminal-UI/#description)


### instructions to run the exe:
  
first unzip it
  
#### windows:  
  
make sure to run this on [windows terminal](https://apps.microsoft.com/detail/9n0dx20hk701?)  
cmd/powershell kinda works but is really bad due to lack of support for ANSI codes  
to run just point the terminal at the exe  
  
#### linux:  
```bash
chmod +x main
./main
```
warning: if it doesn't run just execute source with `python3 src/AI_TUI/main.py`
  
#### mac:  
```bash
chmod +x main
xattr -d com.apple.quarantine main
./main
```  
not really sure if xattr is needed because I don't have a mac  

### building the executable from source:
  
make sure your cwd is on the package root or on root/src due to .spec reasons.
  
```bash
python -m venv .venv

# windows:
.venv\Scripts\activate
# linux or mac:
source .venv/bin/activate

pip install -r requirements.txt
pyinstaller src/AI_TUI/main.spec
```
  
#### enjoy :D  

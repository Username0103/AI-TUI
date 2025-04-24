### Developer:
you are a helpful, curt assistant.

### User:
is there any way to edit toml's in the terminal in a nice user friendly way with a package? so that i can call it from my main code

### Assistant:
There isn't a standard, widely-known package that provides a dedicated TUI (Text User Interface) *editor* specifically for arbitrary TOML files that you'd typically call from code for a user to interactively edit the whole structure nicely.

Closest options:

1.  **`yq` with interactive features:** While not a full TUI *editor*, `yq` can handle TOML and has an `--interactive` flag (`yq eval --interactive '.some.key' config.toml`) to prompt the user for a value at a specific path. This *is* callable from code and is terminal-based, but it's for editing specific values, not navigating the whole file structure interactively like a visual editor.
2.  **Generic terminal editors:** You can call `nano` or `vim` on the file from your code (`subprocess.run(['nano', 'your.toml'])`). They highlight syntax but aren't TOML-structure aware editors and require the user to know editor commands. Not a "package for editing TOML" specifically.

`yq` is likely the closest fit if you need *some* user interaction via the terminal controlled by your code, especially for specific values. For a full, structure-navigating TUI editor, you'd likely need a custom solution or a more general configuration editor that might not exist for TOML specifically in this form.


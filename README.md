# kiro

A small Python client for [Kiro on the web](https://app.kiro.dev). It opens one session, sends a prompt, and prints the reply.

```bash
python3 kiro.py --cookie-file session.txt --prompt "Say hello"
```

`session.txt` is a single line copied from your browser's cookie header for `app.kiro.dev`.

```text
python3 kiro.py --help
```

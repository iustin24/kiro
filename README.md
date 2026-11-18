# kiro

A small Python client for [Kiro on the web](https://app.kiro.dev). It opens one session, sends a prompt, and prints the reply.

```bash
python3 kiro.py --profile profile.txt --prompt "Say hello"
```

`profile.txt` is one line:

```text
login=...; idp=Github; renew=...; uid=...
```

`login` and `renew` are the two long values from the browser. This client fills in the header names the site expects.

```text
python3 kiro.py --help
```

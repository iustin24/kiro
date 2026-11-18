# kiro

A small Python client for [Kiro on the web](https://app.kiro.dev). It opens one session, sends a prompt, and prints the reply.

```bash
python3 kiro.py --profile notes.txt --prompt "Say hello"
```

`notes.txt` is one line. Copy each value from the browser cookie of the same name:

```text
AccessToken=<AccessToken>; Idp=<Idp>; RefreshToken=<RefreshToken>; UserId=<UserId>
```

```text
python3 kiro.py --help
```

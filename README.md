# ytb-reproduction

```bash
echo 'export GEMINI_API_KEY="AI**********"' >> ~/.bashrc
source ~/.bashrc
```



```bash
sudo python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
mv biliup_rs venv/bin/biliup_rs
biliup_rs login
```

```bash
sudo apt update
sudo apt install -y tigervnc-standalone-server xfce4 xfce4-goodies
sudo apt install -y novnc websockify
```

```bash
vncserver :1
vncserver -kill :1
```

```~/.vnc/xstartup
#!/bin/bash
xrdb $HOME/.Xresources
startxfce4 &
```

```bash
chmod +x ~/.vnc/xstartup
```

```bash
vncserver :1
```

```bash
screen -S novnc
screen -r novnc
websockify --web=/usr/share/novnc/ 6080 localhost:5901
```

http://ip:6080/vnc.html

```bash
sudo snap install firefox
firefox
```

optional

```bash
DISPLAY=:1 firefox
```

```bash
ls ~/.mozilla/firefox/
```

```python
'cookiesfrombrowser': ('firefox', 'abcdefg.default-release'),
```

#!/usr/bin/env python3
"""Render one reel from a JSON spec.  Usage: make_reel.py spec.json out.mp4
Spec: {"shift": 0, "scenes": [{"size": 150, "num": "01"(optional), "lines": ["text ..."]}]}
Line syntax: words separated by spaces. "*word" = accent colour. "shown|spoken_words" = show one
thing, speak another (underscores = spaces), e.g. "*23|twenty-three". "|One." = spoken only.
Real footage: add "bg" to a scene (or to the spec as a default for scenes without one):
  "bg": "pipeline/.cache/stock/pexels_123.mp4"  or  {"src": ..., "start": 2, "focus": [0.5,0.4], "dim": 0.5}
Video clips play under the text; photos get a slow push-in. See pipeline/bgmedia.py. Scenes without
a bg use the plain dark brand background.
Also writes <out>.sheet.png (one frame per scene) for visual checking."""
import numpy as np, soundfile as sf, subprocess, sys, json, os, tempfile
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import bgmedia
from kokoro_onnx import Kokoro
HERE=os.path.dirname(os.path.abspath(__file__))
W,H,FPS=1080,1920,30
BG=(14,15,17);FG=(244,242,236);AC=(198,255,61)
BLACK=HERE+"/fonts/InterDisplay-Black.otf"; BOLD=HERE+"/fonts/Inter-Bold.otf"
X0=96; MAXW=W-2*X0; VOICE="am_michael"
k=Kokoro(HERE+"/.cache/kokoro-v1.0.onnx",HERE+"/.cache/voices-v1.0.bin")
fonts={}
def F(p,s):
    if (p,s) not in fonts: fonts[(p,s)]=ImageFont.truetype(p,s)
    return fonts[(p,s)]
def P(s):
    out=[]
    for tok in s.split():
        d,sp=tok.split("|",1) if "|" in tok else (tok,None)
        if sp is None: sp=d.lstrip("*")
        out.append((d,sp.replace("_"," ")))
    return out
def tts(text):
    s,sr=k.create(text,voice=VOICE,speed=1.02,lang="en-us"); s=np.asarray(s,dtype=np.float32)
    idx=np.where(np.abs(s)>0.012)[0]; pad=int(0.03*sr)
    return s[max(idx[0]-pad,0):idx[-1]+pad],sr
def music(dur,shift=0,sr=44100):
    r=2**(shift/12); tt_=np.arange(int(dur*sr))/sr; out=np.zeros_like(tt_); beat=60/84; seg=8*beat
    chords=[[73.42,110.0,146.83,174.61,220.0,261.63],[58.27,116.54,146.83,174.61,233.08,293.66]]
    for i,st in enumerate(np.arange(0,dur,seg)):
        m=(tt_>=st)&(tt_<st+seg+0.6); x=tt_[m]-st; env=np.clip(x/1.2,0,1)*np.clip((seg+0.6-x)/1.2,0,1)
        ch=[f*r for f in chords[i%2]]; s=sum(np.sin(2*np.pi*f*x+j)*(0.5/(1+j*0.25)) for j,f in enumerate(ch))
        s+=sum(np.sin(2*np.pi*f*1.004*x)*0.12 for f in ch[2:]); out[m]+=s*env*0.12
    for b in np.arange(0,dur-0.3,2*beat):
        i0=int(b*sr); n=int(0.25*sr); x=np.arange(n)/sr; f=44+60*np.exp(-x*28)
        out[i0:i0+n]+=np.sin(2*np.pi*np.cumsum(f)/sr)*np.exp(-x*14)*0.30
    fi=int(0.4*sr); fo=int(1.0*sr); out[:fi]*=np.linspace(0,1,fi); out[-fo:]*=np.linspace(1,0,fo)
    return out/np.abs(out).max()*0.8
yy,xx=np.mgrid[0:1700,0:1700]; r_=np.hypot(xx-850,yy-850)/850
glow=Image.fromarray((np.clip(1-r_,0,1)**2.2*46).astype(np.uint8)); glowc=Image.new("RGB",(1700,1700),AC)
ease=lambda u:1-(1-min(max(u,0),1))**3
def layout(sc):
    size=sc.get("size",128)
    while True:
        f=F(BLACK,size); lh=int(size*1.04); sp=f.getlength(" ")*0.9; y=140 if sc.get("num") else 0; words=[]; mw=0
        for li,line in enumerate(sc["pl"]):
            x=0
            for wi,(disp,_) in enumerate(line):
                if not disp: continue
                acc=disp.startswith("*"); d=disp.lstrip("*"); wl=f.getlength(d); mw=max(mw,wl)
                if x>0 and x+wl>MAXW: x=0; y+=lh
                words.append((d,x,y,acc,li,wi)); x+=wl+sp
            y+=lh+int(size*0.22)
        h=y-int(size*0.22)
        if (mw<=MAXW and h<=960) or size<=60: break
        size-=6
    sc.update(words=words,h=h,y0=900-h//2,fsize=size)
def build(spec,out):
    scenes=spec["scenes"]; shift=spec.get("shift",0); tmp=tempfile.mkdtemp()
    t=0.20; voice=[]; SR=24000
    for sc in scenes:
        sc["pl"]=[P(l) for l in sc["lines"]]; sc["start"]=max(t-0.12,0); sc["lt"]=[]
        for line in sc["pl"]:
            a,sr=tts(" ".join(sp for _,sp in line)); d=len(a)/sr
            w=[len(sp)+(5 if sp[-1] in ".,:?" and i<len(line)-1 else 0) for i,(_,sp) in enumerate(line)]
            cum=np.concatenate([[0],np.cumsum(w)])/sum(w)
            sc["lt"].append({"start":t,"wt":[t+d*c for c in cum[:-1]]}); voice.append((t,a)); t+=d+0.16
        t+=0.20; sc["end"]=t-0.12; layout(sc)
    scenes[0]["start"]=0; TOTAL=t+0.5; scenes[-1]["end"]=TOTAL
    for sc in scenes:
        b=bgmedia.norm(sc.get("bg",spec.get("bg")))
        sc["clip"]=bgmedia.Clip(b,W,H,FPS,sc["end"]-sc["start"]) if b else None
    v=np.zeros(int(TOTAL*SR)+SR*8,dtype=np.float32)
    for st,a in voice: i=int(st*SR); v[i:i+len(a)]+=a
    v=v[:int(TOTAL*SR)]; v*=0.9/np.abs(v).max(); sf.write(tmp+"/voice.wav",v,SR); sf.write(tmp+"/music.wav",music(TOTAL,shift),44100)
    def frame(tm):
        cur=[s for s in scenes if s["start"]<=tm<s["end"]] or [scenes[-1]]; sc=cur[0]
        if sc["clip"]:
            im=sc["clip"].frame(tm-sc["start"]).convert("RGBA")
            im=Image.alpha_composite(im,bgmedia.scrim(W,H,0.5,(sc["y0"]+sc["h"]/2)/H))
        else:
            im=Image.new("RGB",(W,H),BG)
            im.paste(glowc,(int(-500+260*np.sin(tm*0.22+shift)),int(700+320*np.cos(tm*0.17+shift))),glow)
            im=im.convert("RGBA")
        ov=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(ov)
        d.ellipse([X0,318,X0+18,336],fill=AC+(255,)); x=X0+34
        for c in "OPERATOR HABITS":
            d.text((x,309),c,font=F(BOLD,30),fill=FG+(165,)); x+=F(BOLD,30).getlength(c)+5
        first=sc is scenes[0]
        e=1.0 if first else ease((tm-sc["start"])/0.22); off=int((1-e)*34); f=F(BLACK,sc["fsize"])
        if sc.get("num"): d.text((X0,sc["y0"]+off),sc["num"],font=F(BLACK,96),fill=AC+(int(255*e),))
        for (w,x,y,acc,li,wi) in sc["words"]:
            lt=sc["lt"][li]
            if tm<lt["start"]-0.08 and not first: continue
            lit=min(max((tm-lt["wt"][wi]+0.04)/0.09,0),1); a=(0.26+0.74*lit)*e
            col=tuple(int(FG[i]+(AC[i]-FG[i])*lit) for i in range(3)) if acc else FG
            d.text((X0+x,sc["y0"]+y+off),w,font=f,fill=col+(int(255*a),))
        if sc["clip"]:  # soft shadow so text holds up on busy footage
            sh=Image.new("RGBA",(W,H),(0,0,0,0)); sh.putalpha(ov.getchannel("A").point(lambda a:a*0.7).filter(ImageFilter.GaussianBlur(14)))
            im=Image.alpha_composite(im,sh)
        return Image.alpha_composite(im,ov).convert("RGB")
    p=subprocess.Popen(["ffmpeg","-loglevel","error","-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-","-i",tmp+"/voice.wav","-i",tmp+"/music.wav",
     "-filter_complex","[0:v]noise=alls=3[v];[1:a]aresample=44100[a1];[2:a]volume=0.22[a2];[a1][a2]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]",
     "-map","[v]","-map","[a]","-c:v","libx264","-preset","medium","-crf","21","-maxrate","8M","-bufsize","16M","-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-ar","44100","-movflags","+faststart","-shortest",out],stdin=subprocess.PIPE)
    for i in range(int(TOTAL*FPS)): p.stdin.write(frame(i/FPS).tobytes())
    p.stdin.close(); p.wait()
    n=len(scenes); sheet=Image.new("RGB",(270*n,480))
    for i,s in enumerate(scenes): sheet.paste(frame(s["end"]-0.15).resize((270,480)),(i*270,0))
    sheet.save(out+".sheet.png")
    for s in scenes:
        if s["clip"]: s["clip"].close()
    print(json.dumps({"out":out,"seconds":round(TOTAL,1),"font_sizes":[s["fsize"] for s in scenes]}))
if __name__=="__main__":
    build(json.load(open(sys.argv[1])),sys.argv[2])

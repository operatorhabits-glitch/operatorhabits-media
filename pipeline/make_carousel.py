#!/usr/bin/env python3
"""Render a carousel from a JSON spec.  Usage: make_carousel.py spec.json out_prefix
Writes <out_prefix>_1.png ... _N.png (1080x1350) and <out_prefix>_sheet.png for checking.
Spec: {"slides": [{"tag": "hook"|"01".."09"|"end", "title": "Text with *accent words.", "body": "Plain text."}]}"""
import numpy as np, sys, json, os
from PIL import Image, ImageDraw, ImageFont
HERE=os.path.dirname(os.path.abspath(__file__))
W,H=1080,1350; BG=(14,15,17);FG=(244,242,236);AC=(198,255,61); X0=96; MAXW=W-2*X0
F=lambda n,s:ImageFont.truetype(HERE+"/fonts/"+n,s)
yy,xx=np.mgrid[0:1500,0:1500]; r=np.hypot(xx-750,yy-750)/750
glow=Image.fromarray((np.clip(1-r,0,1)**2.2*44).astype(np.uint8)); glowc=Image.new("RGB",(1500,1500),AC)
def wrap(d,text,font,maxw):
    lines=[];cur=""
    for w in text.split():
        t=(cur+" "+w).strip()
        if d.textlength(t.replace("*",""),font=font)<=maxw: cur=t
        else: lines.append(cur); cur=w
    lines.append(cur); return [l for l in lines if l]
def rich(d,x,y,line,font):
    for w in line.split():
        acc=w.startswith("*"); w=w.lstrip("*")
        d.text((x,y),w,font=font,fill=(AC if acc else FG)+(255,)); x+=d.textlength(w+" ",font=font)
def build(spec,prefix):
    slides=spec["slides"]; n=len(slides); outs=[]
    for i,s in enumerate(slides):
        tag,title,body=s["tag"],s["title"],s.get("body","")
        im=Image.new("RGB",(W,H),BG); im.paste(glowc,(-420+i*90,560-i*40),glow); im=im.convert("RGBA")
        ov=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(ov)
        d.ellipse([X0,104,X0+18,122],fill=AC+(255,)); x=X0+34
        for c in "OPERATOR HABITS": d.text((x,95),c,font=F("Inter-Bold.otf",30),fill=FG+(165,)); x+=d.textlength(c,font=F("Inter-Bold.otf",30))+5
        big=tag in("hook","end"); ts=132 if tag=="hook" else 112 if tag=="end" else 104
        while True:
            tf=F("InterDisplay-Black.otf",ts); tl=wrap(d,title,tf,MAXW)
            if (max(d.textlength(l.replace("*",""),font=tf) for l in tl)<=MAXW and len(tl)<=5) or ts<=60: break
            ts-=6
        bf=F("Inter-Regular.otf",48); bl=wrap(d,body,bf,MAXW-40) if body else []
        hgt=(170 if not big else 0)+len(tl)*int(ts*1.05)+56+len(bl)*68; y=(H-hgt)//2+10
        if not big: d.text((X0,y),tag,font=F("InterDisplay-Black.otf",120),fill=AC+(255,)); y+=170
        for l in tl: rich(d,X0,y,l,tf); y+=int(ts*1.05)
        y+=56
        for l in bl: d.text((X0,y),l,font=bf,fill=FG+(190,)); y+=68
        for j in range(n):
            cx=X0+j*30; d.ellipse([cx,1232,cx+12,1244],fill=(AC if j==i else FG)+((255 if j==i else 70),))
        if i<n-1:
            ax=W-X0; d.line([ax-70,1238,ax,1238],fill=FG+(200,),width=5); d.line([ax-22,1218,ax,1238,ax-22,1258],fill=FG+(200,),width=5,joint="curve")
        o=f"{prefix}_{i+1}.png"; Image.alpha_composite(im,ov).convert("RGB").save(o); outs.append(o)
    sheet=Image.new("RGB",(270*n,338))
    for i,o in enumerate(outs): sheet.paste(Image.open(o).resize((270,338)),(i*270,0))
    sheet.save(prefix+"_sheet.png"); print(json.dumps({"slides":outs}))
if __name__=="__main__":
    build(json.load(open(sys.argv[1])),sys.argv[2])

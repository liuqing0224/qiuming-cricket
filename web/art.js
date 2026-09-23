// Original procedural game art. Coordinates describe an articulated cricket, facing right.
export function cricket(ctx,x,y,scale,color,flip=1,time=0,pose='idle'){
 ctx.save();ctx.translate(x,y);ctx.scale(scale*flip,scale);ctx.rotate(-.10);
 const wiggle=Math.sin(time*3)*2;
 const stroke=(points,width,col)=>{ctx.beginPath();ctx.moveTo(...points[0]);for(let i=1;i<points.length;i++)ctx.lineTo(...points[i]);ctx.strokeStyle=col;ctx.lineWidth=width;ctx.lineCap='round';ctx.lineJoin='round';ctx.stroke()};
 const ellipse=(x,y,rx,ry,angle,fill,outline)=>{ctx.beginPath();ctx.ellipse(x,y,rx,ry,angle,0,Math.PI*2);ctx.fillStyle=fill;ctx.fill();if(outline){ctx.strokeStyle=outline;ctx.lineWidth=.8;ctx.stroke()}};
 ctx.save();ctx.scale(1,.4);ellipse(-3,17,61,26,0,'#202a2030');ctx.restore();
 // Three jointed pairs of legs, including the strong rear femora.
 for(const side of [-1,1]){
  const s=side;const gait=pose==='attack'?Math.sin(time*18)*7:wiggle;
  stroke([[-15,s*8],[-48,s*(34+gait)],[-33,s*46],[-65,s*53]],2.1,'#514931');
  stroke([[-15,s*9],[-47,s*(33+gait)]],7,'#766947');
  stroke([[-13,s*10],[-46,s*(32+gait)]],3,color);
  for(let k=0;k<5;k++)stroke([[-42+k*2,s*(37+k*1.3)],[-47+k*2,s*(41+k*1.3)]],.7,'#504c34');
  stroke([[8,s*11],[-1,s*(28+gait)],[-11,s*39],[-5,s*44]],1.8,'#55573b');
  stroke([[23,s*9],[38,s*(23-gait)],[48,s*22],[53,s*27]],1.7,'#58523a');
 }
 // Segmented abdomen and finely veined wing covers.
 let g=ctx.createLinearGradient(-44,-15,20,18);g.addColorStop(0,'#393c2b');g.addColorStop(.45,color);g.addColorStop(1,'#a1925f');
 ellipse(-12,0,34,15,0,g,'#393e2d');
 for(let i=0;i<6;i++){ctx.beginPath();ctx.ellipse(-35+i*6,0,4,12-i*.5,0,-1.25,1.25);ctx.strokeStyle='#b1a16c55';ctx.lineWidth=.8;ctx.stroke()}
 ellipse(-15,-5,29,8,-.08,color,'#b6ac7970');ellipse(-15,5,29,8,.08,color,'#a5a07180');
 stroke([[-43,0],[11,0]],1,'#242f21');
 for(let i=0;i<9;i++){stroke([[-36+i*5,0],[-24+i*4,-10+Math.abs(i-4)]],.55,'#c3b78590');stroke([[-36+i*5,0],[-24+i*4,10-Math.abs(i-4)]],.55,'#c3b78570')}
 g=ctx.createLinearGradient(8,-12,29,12);g.addColorStop(0,'#b1a574');g.addColorStop(.4,color);g.addColorStop(1,'#2c3929');ellipse(17,0,13,15,0,g,'#343b26');
 stroke([[12,-12],[11,11]],1,'#b4ac7c');
 g=ctx.createRadialGradient(31,-5,0,32,0,14);g.addColorStop(0,'#9e9663');g.addColorStop(.5,'#4e5738');g.addColorStop(1,'#273124');ellipse(32,0,12,12,0,g,'#32382b');
 ellipse(36,-9,3.5,3,-.3,'#20281b');ellipse(36,9,3.5,3,.3,'#20281b');ellipse(37,-10,1,1,0,'#c3bb8c');
 stroke([[40,-5],[47,-5],[48,-1]],2.5,'#75623c');stroke([[40,5],[47,5],[48,1]],2.5,'#75623c');
 // Long antennae respond to each stance.
 for(const s of [-1,1]){ctx.beginPath();ctx.moveTo(36,s*5);ctx.bezierCurveTo(60,s*(14+wiggle),81,s*(34+wiggle),112,s*(24+wiggle*3));ctx.lineWidth=.85;ctx.strokeStyle='#5e6044';ctx.stroke()}
 stroke([[-44,-4],[-57,-12]],1.1,'#635f3f');stroke([[-44,4],[-57,12]],1.1,'#635f3f');
 ctx.restore();
}

export function drawBowl(ctx,w,h,t,{player,enemy,animation,result,reduced}){
 ctx.clearRect(0,0,w,h);const cx=w/2,cy=h*.43,rx=Math.min(w*.43,h*1.15),ry=Math.min(rx*.57,h*.34);
 const ellipse=(x,y,a,b,fill)=>{ctx.beginPath();ctx.ellipse(x,y,a,b,0,0,Math.PI*2);ctx.fillStyle=fill;ctx.fill()};
 ctx.save();ctx.shadowColor='#46503930';ctx.shadowBlur=22;ctx.shadowOffsetY=15;ellipse(cx,cy+13,rx,ry,'#888978');ctx.restore();
 let rim=ctx.createLinearGradient(cx-rx,cy-ry,cx+rx,cy+ry);rim.addColorStop(0,'#bab7a0');rim.addColorStop(.22,'#e0ddc6');rim.addColorStop(.54,'#aaa991');rim.addColorStop(.8,'#797f69');rim.addColorStop(1,'#b9b9a0');
 ellipse(cx,cy+8,rx,ry,rim);ellipse(cx,cy,rx,ry,rim);
 ctx.beginPath();ctx.ellipse(cx,cy,rx-4,ry-3,0,0,Math.PI*2);ctx.strokeStyle='#eeedd975';ctx.lineWidth=1;ctx.stroke();
 let inside=ctx.createRadialGradient(cx,cy+ry*.3,rx*.1,cx,cy,rx);inside.addColorStop(0,'#d6d4b9');inside.addColorStop(.67,'#c0c1a5');inside.addColorStop(.89,'#898f74');inside.addColorStop(1,'#707961');
 ellipse(cx,cy,rx-13,ry-10,inside);
 ctx.save();ctx.beginPath();ctx.ellipse(cx,cy,rx-15,ry-12,0,0,Math.PI*2);ctx.clip();
 // Reproducible ceramic grain and wheel-thrown concentric grooves.
 for(let i=0;i<1300;i++){const u=Math.sin(i*127.1)*43758.5453,v=Math.sin(i*311.7)*9631.54;const px=cx-rx+((u-Math.floor(u))*rx*2),py=cy-ry+((v-Math.floor(v))*ry*2);ctx.fillStyle=i%3?'#4d583815':'#f2efd640';ctx.fillRect(px,py,i%4===0?1.5:.6,.7)}
 for(let i=0;i<8;i++){ctx.beginPath();ctx.ellipse(cx,cy+5,rx-23-i*4,ry-17-i*2.3,0,0,Math.PI*2);ctx.strokeStyle=i%2?'#4e5b3610':'#ecebd721';ctx.lineWidth=.7;ctx.stroke()}
 const elapsed=animation?Math.min(1,(performance.now()-animation.start)/800):1;
 const burst=animation?Math.sin(elapsed*Math.PI):0;
 let offset=rx*.32;
 const y=cy+ry*.15;
 const ps=animation?.player==='attack'?burst*rx*.25:0,es=animation?.enemy==='attack'?burst*rx*.25:0;
 const scale=Math.min(.82,rx/250);
 cricket(ctx,cx-offset+ps,y-8,scale,player,1,reduced?0:t,animation?.player||'idle');
 cricket(ctx,cx+offset-es,y+14,scale,enemy,-1,reduced?0:t+1,animation?.enemy||'idle');
 if(animation&&elapsed<1){
  for(const [move,side] of [[animation.player,-1],[animation.enemy,1]]){
   const px=cx+side*offset;
   if(move==='guard'){ctx.beginPath();ctx.ellipse(px,y,rx*.19,ry*.37,0,0,Math.PI*2);ctx.strokeStyle=`rgba(85,111,68,${burst*.7})`;ctx.lineWidth=2;ctx.stroke()}
   if(move==='provoke'){
    ctx.beginPath();ctx.moveTo(px+side*rx*.45,cy-ry);ctx.quadraticCurveTo(px+side*20,cy-ry*.4,px-side*22,y-10-burst*8);ctx.strokeStyle='#9c8d4f';ctx.lineWidth=1.7;ctx.stroke();
    for(let j=0;j<9;j++){ctx.beginPath();ctx.moveTo(px-side*22,y-10-burst*8);ctx.lineTo(px-side*22+Math.cos(j*.6)*13,y-18-burst*8+Math.sin(j*.6)*10);ctx.strokeStyle='#b3a06a';ctx.lineWidth=.7;ctx.stroke()}
   }
  }
 }
 if(burst>.5 && (ps||es)){for(let i=0;i<7;i++){const a=i/7*Math.PI*2;ctx.beginPath();ctx.moveTo(cx+Math.cos(a)*12,y+Math.sin(a)*12);ctx.lineTo(cx+Math.cos(a)*(20+burst*9),y+Math.sin(a)*(20+burst*9));ctx.strokeStyle=`rgba(167,131,68,${burst*.6})`;ctx.lineWidth=1.5;ctx.stroke()}}
 ctx.restore();
 // Quiet floating dust above the bowl, with no motion when reduced motion is requested.
 if(!reduced){for(let i=0;i<7;i++){let a=t*.07+i*2;ellipse(cx+Math.sin(a)*rx*.85,cy+Math.cos(a*1.7)*ry*.8,1,1,'#e9e8c795')}}
}

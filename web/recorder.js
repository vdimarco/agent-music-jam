class JamRecorder extends AudioWorkletProcessor {
  constructor(){super();this.active=false;this.buffer=new Float32Array(4096);this.index=0;this.port.onmessage=({data})=>{if(data==='start'){this.active=true;this.index=0;}if(data==='stop'){this.active=false;if(this.index)this.port.postMessage(this.buffer.slice(0,this.index));this.index=0;this.port.postMessage('flushed');}};}
  process(inputs,outputs){const input=inputs[0]?.[0];const output=outputs[0]?.[0];if(input&&output)output.set(input);if(this.active&&input){for(const x of input){this.buffer[this.index++]=x;if(this.index===4096){this.port.postMessage(this.buffer.slice());this.index=0;}}}return true;}
}
registerProcessor('jam-recorder',JamRecorder);

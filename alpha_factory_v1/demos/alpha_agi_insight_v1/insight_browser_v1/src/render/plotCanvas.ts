// SPDX-License-Identifier: Apache-2.0
type PlotContext = { gl: WebGLRenderingContext; program: WebGLProgram; positions: WebGLBuffer; colors: WebGLBuffer };
const ctxCache = new WeakMap<HTMLCanvasElement, PlotContext>();

function createContext(canvas: HTMLCanvasElement): PlotContext {
  const gl = canvas.getContext('webgl');
  if (!gl) throw new Error('WebGL is unavailable');
  const program = gl.createProgram()!;
  const shaders = [
    [gl.VERTEX_SHADER, `attribute vec2 position; attribute vec4 color; varying vec4 vColor;
      void main() { vColor = color; gl_PointSize = 6.0; gl_Position = vec4(position, 0.0, 1.0); }`],
    [gl.FRAGMENT_SHADER, `precision mediump float; varying vec4 vColor;
      void main() { gl_FragColor = vColor; }`],
  ] as const;
  for (const [kind, source] of shaders) {
    const shader = gl.createShader(kind)!;
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader) || 'Shader failed');
    gl.attachShader(program, shader);
    gl.deleteShader(shader);
  }
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program) || 'WebGL link failed');
  return { gl, program, positions: gl.createBuffer()!, colors: gl.createBuffer()! };
}

function parseColor(color: string): [number, number, number, number] {
  const c = document.createElement('canvas');
  const ctx = c.getContext('2d')!;
  ctx.fillStyle = color;
  const computed = ctx.fillStyle;
  if (computed.startsWith('#')) {
    const n = parseInt(computed.slice(1), 16);
    const r = (n >> 16) & 255;
    const g = (n >> 8) & 255;
    const b = n & 255;
    return [r / 255, g / 255, b / 255, 1];
  }
  const m = computed.match(/\d+(\.\d+)?/g);
  if (m) {
    return [
      Number(m[0]) / 255,
      Number(m[1]) / 255,
      Number(m[2]) / 255,
      m[3] ? Number(m[3]) : 1,
    ];
  }
  return [0, 0, 0, 1];
}

type NodeParent = HTMLElement | SVGGraphicsElement | { node: () => HTMLElement | SVGGraphicsElement };
function ensureGL(parent: NodeParent): [HTMLCanvasElement, PlotContext] {
  const node: HTMLElement | SVGGraphicsElement = 'node' in parent ? parent.node() : parent;
  let canvas = node.querySelector<HTMLCanvasElement>('canvas.webgl-layer');
  if (!canvas) {
    const svg = (
      'ownerSVGElement' in node ? node.ownerSVGElement || node : node
    ) as unknown as SVGSVGElement;
    const vb = svg.viewBox?.baseVal;
    const width = vb && vb.width ? vb.width : svg.clientWidth;
    const height = vb && vb.height ? vb.height : svg.clientHeight;
    canvas = document.createElement('canvas');
    canvas.className = 'webgl-layer';
    canvas.width = width;
    canvas.height = height;
    canvas.style.position = 'absolute';
    canvas.style.left = '0';
    canvas.style.top = '0';
    canvas.style.pointerEvents = 'none';
    node.appendChild(canvas);
  }
  let regl = ctxCache.get(canvas);
  if (!regl) {
    regl = createContext(canvas);
    ctxCache.set(canvas, regl);
  }
  return [canvas, regl];
}

export function plotCanvas(
  parent: HTMLElement | SVGSVGElement,
  pop: any[],
  x: (d: any) => number,
  y: (d: any) => number,
  colorFn: (d: any) => string,
): void {
  const [canvas, state] = ensureGL(parent);
  const { gl, program, positions, colors } = state;
  gl.viewport(0, 0, canvas.width, canvas.height);
  gl.useProgram(program);
  for (const [name, buffer, width, values] of [
    ['position', positions, 2, pop.flatMap(d => [x(d) / canvas.width * 2 - 1, 1 - y(d) / canvas.height * 2])],
    ['color', colors, 4, pop.flatMap(d => parseColor(colorFn(d)))],
  ] as const) {
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(values), gl.DYNAMIC_DRAW);
    const location = gl.getAttribLocation(program, name);
    gl.enableVertexAttribArray(location);
    gl.vertexAttribPointer(location, width, gl.FLOAT, false, 0, 0);
  }
  gl.clearColor(0, 0, 0, 0);
  gl.clear(gl.COLOR_BUFFER_BIT);
  gl.drawArrays(gl.POINTS, 0, pop.length);
}

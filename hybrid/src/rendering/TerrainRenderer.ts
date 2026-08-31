import * as THREE from "three";
import { distanceToPolyline } from "../domain/geometry";
import type { WorldSpec } from "../domain/schema";

function smoothstep(edge0: number, edge1: number, value: number): number {
  const t = Math.max(0, Math.min(1, (value - edge0) / (edge1 - edge0)));
  return t * t * (3 - 2 * t);
}

function terrainNoise(x: number, z: number): number {
  return Math.sin(x * 0.23) * 0.42 + Math.cos(z * 0.19) * 0.34 + Math.sin((x + z) * 0.41) * 0.18;
}

export class TerrainRenderer {
  readonly group = new THREE.Group();
  readonly semanticMask: THREE.DataTexture;
  readonly waterMaterial: THREE.ShaderMaterial;
  readonly tileCount: number;

  constructor(private readonly world: WorldSpec) {
    this.group.name = "terrain-system";
    const maskWidth = 256;
    const maskHeight = 384;
    this.semanticMask = this.createMask(maskWidth, maskHeight);
    const width = world.grid.width * world.grid.cellSize;
    const height = world.grid.height * world.grid.cellSize;
    const geometry = new THREE.PlaneGeometry(width, height, world.grid.width, world.grid.height);
    geometry.rotateX(-Math.PI / 2);
    const positions = geometry.getAttribute("position");
    for (let index = 0; index < positions.count; index += 1) {
      const x = positions.getX(index);
      const z = positions.getZ(index);
      const pathDistance = Math.min(...world.paths.map((path) => distanceToPolyline([x, z], path.points) - path.width / 2));
      const waterDistance = Math.min(...world.waterBodies.map((water) => distanceToPolyline([x, z], water.centerline) - water.width / 2));
      const flatten = smoothstep(0, 4, Math.max(0, Math.min(pathDistance, waterDistance)));
      positions.setY(index, terrainNoise(x, z) * world.terrain.visualElevation * (0.18 + flatten * 0.82) - 0.08);
    }
    geometry.computeVertexNormals();
    this.tileCount = world.grid.width * world.grid.height;

    const terrainMaterial = new THREE.ShaderMaterial({
      uniforms: { uMask: { value: this.semanticMask }, uDetailScale: { value: world.terrain.detailScale } },
      vertexShader: `
        varying vec2 vUv;
        varying vec3 vWorldPosition;
        varying vec3 vNormalView;
        void main() {
          vUv = uv;
          vec4 worldPosition = modelMatrix * vec4(position, 1.0);
          vWorldPosition = worldPosition.xyz;
          vNormalView = normalize(normalMatrix * normal);
          gl_Position = projectionMatrix * viewMatrix * worldPosition;
        }
      `,
      fragmentShader: `
        uniform sampler2D uMask;
        uniform float uDetailScale;
        varying vec2 vUv;
        varying vec3 vWorldPosition;
        varying vec3 vNormalView;

        float hash(vec2 p) {
          p = fract(p * vec2(123.34, 456.21));
          p += dot(p, p + 45.32);
          return fract(p.x * p.y);
        }
        float noise(vec2 p) {
          vec2 i = floor(p); vec2 f = fract(p); f = f*f*(3.0-2.0*f);
          return mix(mix(hash(i), hash(i+vec2(1,0)), f.x), mix(hash(i+vec2(0,1)), hash(i+vec2(1,1)), f.x), f.y);
        }
        void main() {
          vec3 mask = texture2D(uMask, vUv).rgb;
          float broad = noise(vWorldPosition.xz * uDetailScale);
          float fine = noise(vWorldPosition.xz * 1.65);
          float fleck = smoothstep(0.77, 0.9, noise(vWorldPosition.xz * 3.8));
          vec3 grassA = vec3(0.29, 0.49, 0.25);
          vec3 grassB = vec3(0.42, 0.61, 0.31);
          vec3 grass = mix(grassA, grassB, broad * 0.72 + fine * 0.16) + fleck * vec3(0.025,0.035,0.015);
          vec3 pathA = vec3(0.49, 0.33, 0.19);
          vec3 pathB = vec3(0.66, 0.48, 0.28);
          vec3 path = mix(pathA, pathB, broad * 0.5 + fine * 0.28);
          float pebble = smoothstep(0.82, 0.93, noise(vWorldPosition.xz * 2.9 + 8.0)) * mask.r;
          path += pebble * vec3(0.12, 0.1, 0.075);
          vec3 bank = mix(vec3(0.38,0.35,0.22), vec3(0.57,0.49,0.3), broad);
          vec3 color = mix(grass, bank, mask.b * 0.82);
          color = mix(color, path, smoothstep(0.05, 0.94, mask.r));
          float light = 0.76 + max(0.0, dot(normalize(vNormalView), normalize(vec3(-0.5,0.9,0.3)))) * 0.25;
          gl_FragColor = vec4(color * light, 1.0);
        }
      `,
    });
    const terrain = new THREE.Mesh(geometry, terrainMaterial);
    terrain.name = "blended-terrain-foundation";
    terrain.receiveShadow = true;
    this.group.add(terrain);

    const waterGeometry = new THREE.PlaneGeometry(width, height, 1, 1);
    waterGeometry.rotateX(-Math.PI / 2);
    this.waterMaterial = new THREE.ShaderMaterial({
      uniforms: { uMask: { value: this.semanticMask }, uTime: { value: 0 } },
      vertexShader: `varying vec2 vUv; varying vec3 vWorld; void main(){vUv=uv; vec4 wp=modelMatrix*vec4(position,1.0); vWorld=wp.xyz; gl_Position=projectionMatrix*viewMatrix*wp;}`,
      fragmentShader: `
        uniform sampler2D uMask; uniform float uTime; varying vec2 vUv; varying vec3 vWorld;
        void main(){
          vec3 mask=texture2D(uMask,vUv).rgb;
          if(mask.g < 0.025) discard;
          float waveA=sin(vWorld.x*0.72+uTime*1.3)*0.5+0.5;
          float waveB=sin(vWorld.z*1.15-vWorld.x*0.22-uTime*0.85)*0.5+0.5;
          float ripple=smoothstep(0.9,0.985,waveA*waveB);
          float flow=pow(sin((vWorld.x+vWorld.z)*2.1+uTime*1.6)*0.5+0.5,8.0);
          float shore=1.0-smoothstep(0.18,0.72,mask.g);
          vec3 deep=vec3(0.12,0.38,0.46); vec3 light=vec3(0.31,0.67,0.67);
          vec3 color=mix(deep,light,0.24+waveA*0.12)+ripple*vec3(0.11,0.18,0.17)+flow*vec3(0.025,0.045,0.045)+shore*vec3(0.26,0.29,0.22);
          gl_FragColor=vec4(color,0.88);
        }
      `,
      transparent: true,
      depthWrite: false,
    });
    const water = new THREE.Mesh(waterGeometry, this.waterMaterial);
    water.name = "willowwater-animated-surface";
    water.position.y = 0.13;
    water.receiveShadow = true;
    water.renderOrder = 2;
    this.group.add(water);
  }

  update(time: number): void {
    this.waterMaterial.uniforms.uTime!.value = time;
  }

  private createMask(width: number, height: number): THREE.DataTexture {
    const bytes = new Uint8Array(width * height * 4);
    const worldWidth = this.world.grid.width * this.world.grid.cellSize;
    const worldHeight = this.world.grid.height * this.world.grid.cellSize;
    for (let y = 0; y < height; y += 1) {
      for (let x = 0; x < width; x += 1) {
        const worldPoint: [number, number] = [(x / (width - 1) - 0.5) * worldWidth, (y / (height - 1) - 0.5) * worldHeight];
        const pathDistance = Math.min(...this.world.paths.map((path) => distanceToPolyline(worldPoint, path.points) - path.width / 2));
        const waterDistance = Math.min(...this.world.waterBodies.map((water) => distanceToPolyline(worldPoint, water.centerline) - water.width / 2));
        const pathMask = 1 - smoothstep(-0.55, 1.1, pathDistance);
        const waterMask = 1 - smoothstep(-0.5, 0.85, waterDistance);
        const bankMask = 1 - smoothstep(0, 3.2, Math.abs(waterDistance));
        const offset = (y * width + x) * 4;
        bytes[offset] = Math.round(pathMask * 255);
        bytes[offset + 1] = Math.round(waterMask * 255);
        bytes[offset + 2] = Math.round(bankMask * 255);
        bytes[offset + 3] = 255;
      }
    }
    const texture = new THREE.DataTexture(bytes, width, height, THREE.RGBAFormat);
    texture.colorSpace = THREE.NoColorSpace;
    texture.wrapS = THREE.ClampToEdgeWrapping;
    texture.wrapT = THREE.ClampToEdgeWrapping;
    texture.minFilter = THREE.LinearFilter;
    texture.magFilter = THREE.LinearFilter;
    texture.needsUpdate = true;
    return texture;
  }
}

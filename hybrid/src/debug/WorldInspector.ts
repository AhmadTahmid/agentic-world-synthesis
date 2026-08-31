export interface InspectorState {
  logicalGrid: boolean;
  collisions: boolean;
  zones: boolean;
  footprints: boolean;
  spawnPoints: boolean;
  assetIds: boolean;
  vegetation: boolean;
  shadows: boolean;
  particles: boolean;
  freezeRandomness: boolean;
}

type InspectorKey = keyof InspectorState;

const labels: Record<InspectorKey, string> = {
  logicalGrid: "Logical terrain grid",
  collisions: "Semantic collision",
  zones: "Zone boundaries",
  footprints: "Object footprints",
  spawnPoints: "Procedural spawn points",
  assetIds: "Asset IDs",
  vegetation: "Vegetation",
  shadows: "Shadows",
  particles: "Atmospheric particles",
  freezeRandomness: "Freeze seeded randomness",
};

export class WorldInspector {
  readonly state: InspectorState = {
    logicalGrid: false,
    collisions: false,
    zones: false,
    footprints: false,
    spawnPoints: false,
    assetIds: false,
    vegetation: true,
    shadows: true,
    particles: true,
    freezeRandomness: true,
  };
  visible = false;

  constructor(private readonly element: HTMLElement, private readonly onChange: (state: InspectorState) => void, onRegenerate: () => void) {
    const controls = (Object.keys(this.state) as InspectorKey[]).map((key) => `<label><input type="checkbox" data-key="${key}" ${this.state[key] ? "checked" : ""}/> ${labels[key]}</label>`).join("");
    element.innerHTML = `<header><div><span class="eyebrow">Developer mode</span><h2>World Inspector</h2></div><button data-close aria-label="Close inspector">×</button></header><div class="inspector-controls">${controls}</div><button class="regenerate" data-regenerate>Regenerate scatter</button><p class="inspector-note">Orange points are derived placements. Red areas are gameplay collision; visible meshes never define it.</p>`;
    element.querySelectorAll<HTMLInputElement>("input[data-key]").forEach((input) => input.addEventListener("change", () => {
      const key = input.dataset.key as InspectorKey;
      this.state[key] = input.checked;
      this.onChange(this.state);
    }));
    element.querySelector("[data-close]")?.addEventListener("click", () => this.setVisible(false));
    element.querySelector("[data-regenerate]")?.addEventListener("click", onRegenerate);
    window.addEventListener("keydown", (event) => {
      if (event.code === "KeyI" && !event.repeat) this.setVisible(!this.visible);
    });
  }

  setVisible(visible: boolean): void {
    this.visible = visible;
    this.element.classList.toggle("open", visible);
  }

  setSemanticPreset(enabled: boolean): void {
    this.state.logicalGrid = enabled;
    this.state.collisions = enabled;
    this.state.zones = enabled;
    this.state.spawnPoints = enabled;
    this.element.querySelectorAll<HTMLInputElement>("input[data-key]").forEach((input) => {
      const key = input.dataset.key as InspectorKey;
      input.checked = this.state[key];
    });
    this.setVisible(enabled);
    this.onChange(this.state);
  }
}

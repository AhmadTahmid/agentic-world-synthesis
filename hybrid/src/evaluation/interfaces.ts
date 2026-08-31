import type { AssetRegistrySpec, WorldSpec } from "../domain/schema";

/** Future boundary: interpret flattened evidence into semantic observations, never renderer code. */
export interface SceneInterpreter<TReference, TObservation> {
  interpret(reference: TReference): Promise<TObservation>;
}

/** Future boundary: rank known registry entries for an observed semantic role. */
export interface AssetMatcher<TObservation> {
  match(observation: TObservation, registry: AssetRegistrySpec): Promise<readonly string[]>;
}

/** Future boundary: propose a validated declarative WorldSpec from reviewed observations. */
export interface WorldPlanner<TObservation> {
  plan(observation: TObservation, registry: AssetRegistrySpec): Promise<WorldSpec>;
}

export interface RenderEvaluation {
  score: number;
  observations: readonly string[];
  suggestedSpecChanges: readonly string[];
}

/** Future boundary: compare a deterministic render with a target and return critique, not code. */
export interface RenderEvaluator<TReference, TRender> {
  evaluate(reference: TReference, render: TRender, world: WorldSpec): Promise<RenderEvaluation>;
}

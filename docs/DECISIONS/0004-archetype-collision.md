# ADR 0004: Collision belongs to asset archetypes

Status: Accepted

Each archetype declares its ground anchor and collision as none, rectangle, tile mask, or polygon. Doorway sockets subtract explicit cells. Instances refer to that contract.

No sprite-percentage heuristic is permitted. Art replacement must preserve or deliberately version semantic footprints.

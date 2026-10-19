import quiet from "./scenarios/0.json";
import single from "./scenarios/1.json";
import escalation from "./scenarios/2.json";
import recovery from "./scenarios/3.json";
import fault from "./scenarios/4.json";
import boundary from "./scenarios/5.json";
import type { Input } from "./types";
export const SCENARIOS: { name: string; samples: Input[] }[] = [
  quiet,
  single,
  escalation,
  recovery,
  fault,
  boundary,
];

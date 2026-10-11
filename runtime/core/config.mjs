import { readFile } from 'node:fs/promises';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { mergePolicy, DEFAULT_POLICY, PROFILES } from './engine.mjs';

export function policyLocation() {
  return process.env.LACONIC_CONFIG || join(homedir(), '.config','laconic','config.json');
}
export async function loadPolicy() {
  try {
    const obj=JSON.parse(await readFile(policyLocation(),'utf8'));
    if (!obj || typeof obj!=='object'||Array.isArray(obj)) return DEFAULT_POLICY;
    const validated={};
    if (typeof obj.enabled==='boolean')validated.enabled=obj.enabled;
    // LACONIC_PROFILE lets a harness/session choose a task profile without editing config.
    const profile=process.env.LACONIC_PROFILE || obj.profile;
    if (Object.hasOwn(PROFILES,profile)) validated.profile=profile;
    if (obj.diagnostics && typeof obj.diagnostics==='object') {
      validated.diagnostics={};
      if (Number.isSafeInteger(obj.diagnostics.maxGroups) && obj.diagnostics.maxGroups>=1 && obj.diagnostics.maxGroups<=200)
        validated.diagnostics.maxGroups=obj.diagnostics.maxGroups;
      if (Number.isSafeInteger(obj.diagnostics.context) && obj.diagnostics.context>=0 && obj.diagnostics.context<=20)
        validated.diagnostics.context=obj.diagnostics.context;
    }
    if (Number.isSafeInteger(obj.minBytes) && obj.minBytes>=512)validated.minBytes=obj.minBytes;
    if (obj.budgets && typeof obj.budgets==='object') {
      validated.budgets={};
      for(const [name,value] of Object.entries(obj.budgets))
        if (Number.isSafeInteger(value) && value>=512 && value<=1_000_000) validated.budgets[name]=value;
    }
    if (Array.isArray(obj.allowedCategories)) validated.allowedCategories=obj.allowedCategories.filter(x=>['shell','test','search','file','git','unknown'].includes(x));
    if (obj.recovery && typeof obj.recovery==='object') {
      validated.recovery={};
      if(typeof obj.recovery.enabled==='boolean')validated.recovery.enabled=obj.recovery.enabled;
      if(Number.isSafeInteger(obj.recovery.maxStoredBytes) && obj.recovery.maxStoredBytes>=1_024)
        validated.recovery.maxStoredBytes=obj.recovery.maxStoredBytes;
      if(Number.isFinite(obj.recovery.retentionHours) && obj.recovery.retentionHours>=1 && obj.recovery.retentionHours<=720)
        validated.recovery.retentionHours=obj.recovery.retentionHours;
      if(typeof obj.recovery.stats==='boolean')validated.recovery.stats=obj.recovery.stats;
    }
    return mergePolicy(validated);
  } catch {
    return Object.hasOwn(PROFILES,process.env.LACONIC_PROFILE) ? mergePolicy({profile:process.env.LACONIC_PROFILE}) : DEFAULT_POLICY;
  }
}

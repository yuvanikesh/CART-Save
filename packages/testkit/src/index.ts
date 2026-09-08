/**
 * CartGuard AI - Test Kit
 * Per MASTER_PROMPT.md Section 5.232: Inject clocks, ID generators, randomness for deterministic tests
 *
 * Fakes, fixtures, and generators for testing.
 */

import type { Clock, IdGenerator, RandomGenerator } from '@cartguard/domain';

/**
 * Deterministic clock for testing
 */
export class TestClock implements Clock {
  constructor(private fixedTime: Date = new Date('2026-09-08T12:00:00Z')) {}

  now(): Date {
    return new Date(this.fixedTime);
  }

  timestamp(): number {
    return this.fixedTime.getTime();
  }

  advance(ms: number): void {
    this.fixedTime = new Date(this.fixedTime.getTime() + ms);
  }
}

/**
 * Deterministic ID generator for testing
 */
export class TestIdGenerator implements IdGenerator {
  private counter = 0;

  generateId(): string {
    return `test_${String(++this.counter).padStart(8, '0')}`;
  }

  generateEventId(): any {
    return `evt_${String(++this.counter).padStart(8, '0')}` as any;
  }

  generateDecisionId(): any {
    return `dec_${String(++this.counter).padStart(8, '0')}` as any;
  }

  generateSessionId(): any {
    return `ses_${String(++this.counter).padStart(8, '0')}` as any;
  }

  reset(): void {
    this.counter = 0;
  }
}

/**
 * Deterministic random generator for testing
 */
export class TestRandomGenerator implements RandomGenerator {
  constructor(private seed: number = 42) {}

  random(): number {
    // Simple LCG for deterministic "random" numbers
    this.seed = (this.seed * 1664525 + 1013904223) % 4294967296;
    return this.seed / 4294967296;
  }

  randomInt(min: number, max: number): number {
    return Math.floor(this.random() * (max - min + 1)) + min;
  }
}

/**
 * Real implementations for production use
 */
export class SystemClock implements Clock {
  now(): Date {
    return new Date();
  }

  timestamp(): number {
    return Date.now();
  }
}

export class UuidGenerator implements IdGenerator {
  generateId(): string {
    return crypto.randomUUID();
  }

  generateEventId(): any {
    return `evt_${crypto.randomUUID()}` as any;
  }

  generateDecisionId(): any {
    return `dec_${crypto.randomUUID()}` as any;
  }

  generateSessionId(): any {
    return `ses_${crypto.randomUUID()}` as any;
  }
}

export class SystemRandomGenerator implements RandomGenerator {
  random(): number {
    return Math.random();
  }

  randomInt(min: number, max: number): number {
    return Math.floor(Math.random() * (max - min + 1)) + min;
  }
}

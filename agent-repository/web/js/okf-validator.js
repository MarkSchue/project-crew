"use strict";

/* Focused JSON-Schema-subset validator for the SPOC editor (ADR-023).
 *
 * Validates the subset the editor enforces client-side:
 *   type, required, properties (recursive), items, enum, const, pattern,
 *   minLength, minimum.
 * `$ref` and `format` are skipped (accept-anything) — the backend performs
 * full validation on every mutating call, so the client is a UX gate, not
 * a security boundary.
 *
 * The schema itself is fetched from GET /api/v1/schemas/spoc.schema.json,
 * the single source of truth (no vendored copy that can drift).
 */

const OkfValidator = (() => {
  function validate(schema, value, path = "$") {
    const errors = [];
    if (!schema) return errors;

    if (schema.const !== undefined && value !== schema.const) {
      errors.push(`${path}: must equal ${JSON.stringify(schema.const)}`);
      return errors;
    }

    if (schema.enum && !schema.enum.includes(value)) {
      errors.push(`${path}: must be one of ${schema.enum.join(", ")}`);
      return errors;
    }

    const type = schema.type;
    if (type && !matchesType(type, value)) {
      errors.push(`${path}: must be a ${type}`);
      return errors;
    }

    if (type === "string" || typeof value === "string") {
      if (schema.minLength !== undefined && value.length < schema.minLength) {
        errors.push(`${path}: length ${value.length} is less than ${schema.minLength}`);
      }
      if (schema.pattern && typeof value === "string") {
        let re;
        try { re = new RegExp(schema.pattern); } catch (e) { return errors; }
        if (!re.test(value)) errors.push(`${path}: must match /${schema.pattern}/`);
      }
    }

    if (typeof value === "number" && schema.minimum !== undefined && value < schema.minimum) {
      errors.push(`${path}: ${value} is less than ${schema.minimum}`);
    }

    if (schema.properties && value && typeof value === "object") {
      for (const key of Object.keys(schema.properties)) {
        if (key in value) {
          errors.push(...validate(schema.properties[key], value[key], `${path}.${key}`));
        }
      }
    }

    if (schema.required && value && typeof value === "object") {
      for (const key of schema.required) {
        if (!(key in value)) errors.push(`${path}: missing required property '${key}'`);
      }
    }

    if (schema.items && Array.isArray(value)) {
      value.forEach((item, index) => {
        errors.push(...validate(schema.items, item, `${path}[${index}]`));
      });
    }

    return errors;
  }

  function matchesType(type, value) {
    if (Array.isArray(type)) return type.some((t) => matchesType(t, value));
    switch (type) {
      case "object": return value !== null && typeof value === "object" && !Array.isArray(value);
      case "array": return Array.isArray(value);
      case "string": return typeof value === "string";
      case "number": return typeof value === "number";
      case "integer": return typeof value === "number" && Number.isInteger(value);
      case "boolean": return typeof value === "boolean";
      default: return true;
    }
  }

  return { validate };
})();

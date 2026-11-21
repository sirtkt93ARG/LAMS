import test from "node:test";
import assert from "node:assert/strict";
import { roleFromKeycloakRoles } from "./auth.ts";

test("prioriza roles institucionales de Keycloak en el mismo orden que la API", () => {
  assert.equal(roleFromKeycloakRoles(["student"]), "student");
  assert.equal(roleFromKeycloakRoles(["teacher"]), "teacher");
  assert.equal(roleFromKeycloakRoles(["network"]), "network");
  assert.equal(roleFromKeycloakRoles(["admin", "teacher", "network"]), "admin");
  assert.equal(roleFromKeycloakRoles(["teacher", "network"]), "network");
  assert.equal(roleFromKeycloakRoles([]), "student");
});

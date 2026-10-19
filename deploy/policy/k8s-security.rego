package main

import rego.v1

# OPA/conftest policies for Kubernetes manifests (run against `helm template` output).
# `deny` fails the pipeline; `warn` only reports.

# ---- Deny privileged containers ----
deny contains msg if {
	input.kind == "Deployment"
	c := input.spec.template.spec.containers[_]
	c.securityContext.privileged == true
	msg := sprintf("container '%s' must not run privileged", [c.name])
}

# ---- Require resource limits ----
deny contains msg if {
	input.kind == "Deployment"
	c := input.spec.template.spec.containers[_]
	not c.resources.limits
	msg := sprintf("container '%s' must set resources.limits", [c.name])
}

# ---- Require readiness probe ----
deny contains msg if {
	input.kind == "Deployment"
	c := input.spec.template.spec.containers[_]
	not c.readinessProbe
	msg := sprintf("container '%s' must define a readinessProbe", [c.name])
}

# ---- Require liveness probe ----
deny contains msg if {
	input.kind == "Deployment"
	c := input.spec.template.spec.containers[_]
	not c.livenessProbe
	msg := sprintf("container '%s' must define a livenessProbe", [c.name])
}

# ---- Forbid plaintext secrets as literal env values ----
deny contains msg if {
	input.kind == "Deployment"
	c := input.spec.template.spec.containers[_]
	e := c.env[_]
	contains(lower(e.name), "secret")
	e.value
	msg := sprintf("env '%s' looks like a secret but uses a plaintext value; use secretKeyRef", [e.name])
}

# ---- Warn on ':latest' image tag ----
warn contains msg if {
	input.kind == "Deployment"
	c := input.spec.template.spec.containers[_]
	endswith(c.image, ":latest")
	msg := sprintf("container '%s' uses ':latest'; pin an immutable tag", [c.name])
}

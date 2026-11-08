# PBTI path-bound admission policy expressed for Open Policy Agent (Rego v1 syntax).
#
# STATUS (V3): decision and reason parity with the Python PDP (src/pbti/policy.py, PDP._decide with check_origin=True)
# is tested with the rego-cpp interpreter (regopy) by tests/policy_parity/parity_test.py; results in
# results/policy_parity/. The measurements in the paper use the Python PDP. Running this file under OPA itself was
# not possible in the study environment (no approved route to install the OPA binary); the same harness has an
# `--backend opa` mode for that.
#
# input  = {"did", "aid", "wid", "sch", "origin_kind"}   # strings; origin_kind: "device" | "workload"
# data   = the policy document (policies/admission_policy.example.json), loaded as data.pbti
#
# Reasons are produced in the same order as the Python PDP checks them; the first failing check gives the reason.
package pbti.admission

import rego.v1

default allow := false

allow if reason == "PERMIT"

# ------------------------------------------------------------------ input and document validation (fail closed)
input_ok if {
	is_string(input.did)
	is_string(input.aid)
	is_string(input.wid)
	is_string(input.sch)
	is_string(input.origin_kind)
}

str_list(x) if {
	is_array(x)
	every e in x {
		is_string(e)
	}
}

device_entry_ok(d) if {
	is_object(d)
	str_list(object.get(d, "assets", null))
	str_list(object.get(d, "schemas", []))
	object.get(d, "origin", "device") in {"device", "gateway"}
	is_boolean(object.get(d, "active", true))
}

workload_entry_ok(w) if {
	is_object(w)
	str_list(object.get(w, "relay", null))
	is_boolean(object.get(w, "active", true))
}

doc_ok if {
	is_object(data.pbti.devices)
	is_object(data.pbti.workloads)
	every _, d in data.pbti.devices {
		device_entry_ok(d)
	}
	every _, w in data.pbti.workloads {
		workload_entry_ok(w)
	}
}

# ------------------------------------------------------------------ path-bound checks
device := data.pbti.devices[input.did]

workload := data.pbti.workloads[input.wid]

device_active if object.get(device, "active", true) == true

workload_active if object.get(workload, "active", true) == true

required_origin := object.get(device, "origin", "device")

reason := "INPUT_INVALID" if {
	not input_ok
} else := "POLICY_DOCUMENT_INVALID" if {
	not doc_ok
} else := "DEVICE_NOT_REGISTERED" if {
	not device_active
} else := "ASSET_NOT_ASSIGNED" if {
	not input.aid in device.assets
} else := "SCHEMA_NOT_ALLOWED" if {
	not input.sch in object.get(device, "schemas", [])
} else := "WORKLOAD_NOT_REGISTERED" if {
	not workload_active
} else := "PATH_NOT_AUTHORIZED" if {
	not input.did in workload.relay
} else := "ORIGIN_SIGNER_TOO_WEAK" if {
	required_origin == "device"
	input.origin_kind != "device"
} else := "ORIGIN_SIGNER_INVALID" if {
	required_origin == "gateway"
	not input.origin_kind in {"workload", "device"}
} else := "PERMIT"

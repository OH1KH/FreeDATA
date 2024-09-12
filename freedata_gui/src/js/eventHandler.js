import { toRaw } from "vue";
import { displayToast } from "./popupHandler";
import {
  getFreedataMessages,
  getModemState,
  getRadioStatus,
  getSysInfo,
} from "./api";
import { processFreedataMessages } from "./messagesHandler";
import { processRadioStatus } from "./radioHandler";

// ----------------- init pinia stores -------------
import { setActivePinia } from "pinia";
import pinia from "../store/index";
setActivePinia(pinia);
import { useStateStore } from "../store/stateStore";
const stateStore = useStateStore(pinia);
import { useAudioStore } from "../store/audioStore";
const audioStore = useAudioStore(pinia);
import { useSerialStore } from "../store/serialStore";
const serialStore = useSerialStore(pinia);
import { getRemote } from "../store/settingsStore";

export async function loadAllData() {
  let stateData = await getModemState();
  console.log(stateData);
  getSysInfo().then((res) => {
    if (res) {
      stateStore.api_version = res.api_version;
      stateStore.modem_version = res.modem_version;
      stateStore.os_info = res.os_info;
      stateStore.python_info = res.python_info;
    }
  });
  audioStore.loadAudioDevices();
  serialStore.loadSerialDevices();
  console.log(audioStore.audioInputs);
  await getRadioStatus();
  getRemote();
  getOverallHealth();
  getFreedataMessages();
  processFreedataMessages();
  processRadioStatus();
}

export function connectionFailed(endpoint, event) {
  console.log(event);
  stateStore.modem_connection = "disconnected";
}

export function stateDispatcher(data) {
  data = JSON.parse(data);

  if (data.type === "state-change" || data.type === "state") {
    stateStore.modem_connection = "connected";
    stateStore.busy_state = data.is_modem_busy;
    stateStore.channel_busy = data.channel_busy;
    stateStore.is_codec2_traffic = data.is_codec2_traffic;
    stateStore.is_modem_running = data.is_modem_running;
    stateStore.dbfs_level = Math.round(data.audio_dbfs);
    stateStore.dbfs_level_percent = Math.round(
      Math.pow(10, data.audio_dbfs / 20) * 100,
    );
    stateStore.radio_status = data.radio_status;
    stateStore.channel_busy_slot = data.channel_busy_slot;
    stateStore.beacon_state = data.is_beacon_running;
    stateStore.away_from_key = data.is_away_from_key;

    stateStore.activities = Object.entries(data.activities).reverse();
    build_HSL();
  }

  if (data.type === "radio-change" || data.type === "radio") {
    stateStore.s_meter_strength_raw = Math.round(data.s_meter_strength);
    stateStore.s_meter_strength_percent = Math.round(
      Math.pow(10, data.s_meter_strength / 20) * 100,
    );
    stateStore.radio_status = data.radio_status;
    stateStore.frequency = data.radio_frequency;
    stateStore.mode = data.radio_mode;

    let swr = data.radio_swr;
    stateStore.swr_raw = parseFloat(data.radio_swr).toFixed(2);
    if (swr >= 0.0 && swr <= 6.0) {
      swr = (swr / 6.0) * 100;
      stateStore.swr_percent = swr.toFixed(2);
    } else {
      stateStore.swr_percent = 0.0;
    }

    stateStore.tuner = data.radio_tuner;
    stateStore.rf_level = Math.round(data.radio_rf_level / 5) * 5;
  }
}

export function eventDispatcher(data) {
  data = JSON.parse(data);

  if (data.scatter !== undefined) {
    stateStore.scatter = JSON.parse(data.scatter);
    return;
  }

  switch (data["message-db"]) {
    case "changed":
      console.log("fetching new messages...");
      var messages = getFreedataMessages();
      processFreedataMessages(messages);
      return;
  }

  switch (data.ptt) {
    case true:
    case false:
      stateStore.ptt_state = data.ptt;
      return;
  }

  switch (data.modem) {
    case "started":
      displayToast("success", "bi-arrow-left-right", "Modem started", 5000);
      loadAllData();
      return;

    case "stopped":
      displayToast("warning", "bi-arrow-left-right", "Modem stopped", 5000);
      return;

    case "restarted":
      displayToast("secondary", "bi-bootstrap-reboot", "Modem restarted", 5000);
      loadAllData();
      return;

    case "failed":
      displayToast(
        "danger",
        "bi-bootstrap-reboot",
        "Modem startup failed | bad config?",
        5000,
      );
      return;
  }

  var message = "";
  console.log(data);
  switch (data.type) {
    case "hello-client":
      message = "Connected to server";
      displayToast("success", "bi-ethernet", message, 5000);
      stateStore.modem_connection = "connected";

      loadAllData();
      return;

    case "frame-handler":
      switch (data.received) {
        case "CQ":
          message = `
      <div>
        <strong>CQ Received:</strong>
        <span class="badge bg-info text-dark">${data.dxcallsign}</span>
        <div class="mt-2">
          <span class="badge bg-secondary">SNR: ${data.snr}</span>
          <span class="badge bg-warning text-dark">Grid Square: ${data.gridsquare}</span>
        </div>
      </div>
    `;
          displayToast("info", "bi-info-circle", message, 5000);
          break;

        case "QRV":
          message = `
      <div>
        <strong>QRV Received:</strong>
        <span class="badge bg-info text-dark">${data.dxcallsign}</span>
        <div class="mt-2">
          <span class="badge bg-secondary">SNR: ${data.snr}</span>
          <span class="badge bg-warning text-dark">Grid Square: ${data.gridsquare}</span>
        </div>
      </div>
    `;
          displayToast("info", "bi-info-circle", message, 5000);
          break;

        case "PING":
          message = `
      <div>
        <strong>PING Received:</strong>
        <span class="badge bg-info text-dark">${data.dxcallsign}</span>
        <div class="mt-2">
          <span class="badge bg-secondary">SNR: ${data.snr}</span>
        </div>
      </div>
    `;
          displayToast("warning", "bi-exclamation-circle", message, 5000);
          break;

        case "PING_ACK":
          message = `
      <div>
        <strong>PING_ACK Received:</strong>
        <span class="badge bg-info text-dark">${data.dxcallsign}</span>
        <div class="mt-2">
          <span class="badge bg-secondary">SNR: ${data.snr}</span>
          <span class="badge bg-warning text-dark">Grid Square: ${data.gridsquare}</span>
        </div>
      </div>
    `;
          displayToast("success", "bi-check-circle", message, 5000);
          break;

  default:
    console.log("unknown event data received: ${data.gridsquare}");
}
        return;

    case "arq":
      if (data["arq-transfer-outbound"]) {
        stateStore.arq_is_receiving = false;
        switch (data["arq-transfer-outbound"].state) {
          case "NEW":
            message = `
              <div>
                <strong>New transmission with:</strong>
                <span class="badge bg-info text-dark">${data["arq-transfer-outbound"].dxcall}</span>
                <div class="mt-2">
                  <span class="badge bg-secondary">Session ID: ${data["arq-transfer-outbound"].session_id}</span>
                  <span class="badge bg-warning text-dark">Total Bytes: ${data["arq-transfer-outbound"].total_bytes}</span>
                </div>
              </div>
            `;
            displayToast("success", "bi-check-circle", message, 10000);
            stateStore.dxcallsign = data["arq-transfer-outbound"].dxcall;
            stateStore.arq_transmission_percent = 0;
            stateStore.arq_total_bytes = 0;
            return;
          case "OPEN_SENT":
            message = `
              <div>
                <strong>Opening transmission with:</strong>
                <span class="badge bg-info text-dark">${data["arq-transfer-outbound"].dxcall}</span>
                <div class="mt-2">
                  <span class="badge bg-secondary">Session ID: ${data["arq-transfer-outbound"].session_id}</span>
                  <span class="badge bg-warning text-dark">Total Bytes: ${data["arq-transfer-outbound"].total_bytes}</span>
                </div>
              </div>
            `;
            displayToast("info", "bi-check-circle", message, 10000);
            return;

          case "INFO_SENT":
            console.info("state INFO_SENT needs to be implemented");
            return;

          case "BURST_SENT":
            message = `
              <div>
                <strong>ongoing transmission with:</strong>
                <span class="badge bg-info text-dark">${data["arq-transfer-outbound"].dxcall}</span>
                <div class="mt-2">
                  <span class="badge bg-secondary">Session ID: ${data["arq-transfer-outbound"].session_id}</span>
                  <span class="badge bg-warning text-dark">Received Bytes: ${data["arq-transfer-outbound"].received_bytes}</span>
                  <span class="badge bg-warning text-dark">Total Bytes: ${data["arq-transfer-outbound"].total_bytes}</span>
                </div>
              </div>
            `;
            displayToast("info", "bi-info-circle", message, 5000);
            stateStore.arq_transmission_percent = Math.round(
              (data["arq-transfer-outbound"].received_bytes /
                data["arq-transfer-outbound"].total_bytes) *
                100,
            );
            stateStore.arq_total_bytes =
              data["arq-transfer-outbound"].received_bytes;
            stateStore.arq_speed_list_timestamp.value = toRaw(
              data["arq-transfer-outbound"].statistics.time_histogram,
            );
            stateStore.arq_speed_list_bpm.value = toRaw(
              data["arq-transfer-outbound"].statistics.bpm_histogram,
            );
            stateStore.arq_speed_list_snr.value = toRaw(
              data["arq-transfer-outbound"].statistics.snr_histogram,
            );
            stateStore.speed_level = data["arq-transfer-outbound"].speed_level;
            return;

          case "ABORTING":
            console.info("state ABORTING needs to be implemented");
            return;

          case "ABORTED":
            message = `
              <div>
                <strong>transmission ABORTED with:</strong>
                <span class="badge bg-info text-dark">${data["arq-transfer-outbound"].dxcall}</span>
                <div class="mt-2">
                  <span class="badge bg-primary">STATE: ${data["arq-transfer-outbound"].state}</span>
                  <span class="badge bg-secondary">Session ID: ${data["arq-transfer-outbound"].session_id}</span>
                  <span class="badge bg-warning text-dark">Transmitted Bytes: ${data["arq-transfer-outbound"].received_bytes}</span>
                  <span class="badge bg-warning text-dark">Total Bytes: ${data["arq-transfer-outbound"].total_bytes}</span>
                </div>
              </div>
            `;
            displayToast("warning", "bi-exclamation-triangle", message, 5000);
            stateStore.arq_transmission_percent = 0;
            stateStore.arq_total_bytes = 0;
            return;

          case "ENDED":
            message = `
              <div>
                <strong>transmission ENDED with:</strong>
                <span class="badge bg-info text-dark">${data["arq-transfer-outbound"].dxcall}</span>
                <div class="mt-2">
                  <span class="badge bg-primary">STATE: ${data["arq-transfer-outbound"].state}</span>
                  <span class="badge bg-secondary">Session ID: ${data["arq-transfer-outbound"].session_id}</span>
                  <span class="badge bg-warning text-dark">Transmitted Bytes: ${data["arq-transfer-outbound"].received_bytes}</span>
                  <span class="badge bg-warning text-dark">Total Bytes: ${data["arq-transfer-outbound"].total_bytes}</span>
                </div>
              </div>
            `;
            displayToast("success", "bi-info-circle", message, 5000);
            stateStore.arq_transmission_percent = Math.round(
              (data["arq-transfer-outbound"].received_bytes /
                data["arq-transfer-outbound"].total_bytes) *
                100,
            );
            stateStore.arq_total_bytes =
              data["arq-transfer-outbound"].received_bytes;

            // Reset progressbar values after a delay
            setTimeout(() => {
              stateStore.arq_transmission_percent = 0;
              stateStore.arq_total_bytes = 0;
            }, 5000);
            return;
          case "FAILED":
            message = `
              <div>
                <strong>transmission FAILED with:</strong>
                <span class="badge bg-info text-dark">${data["arq-transfer-outbound"].dxcall}</span>
                <div class="mt-2">
                  <span class="badge bg-primary">STATE: ${data["arq-transfer-outbound"].state}</span>
                  <span class="badge bg-secondary">Session ID: ${data["arq-transfer-outbound"].session_id}</span>
                  <span class="badge bg-warning text-dark">Transmitted Bytes: ${data["arq-transfer-outbound"].received_bytes}</span>
                  <span class="badge bg-warning text-dark">Total Bytes: ${data["arq-transfer-outbound"].total_bytes}</span>
                </div>
              </div>
            `;
            displayToast("danger", "bi-x-octagon", message, 5000);
            // Reset progressbar values after a delay
            setTimeout(() => {
              stateStore.arq_transmission_percent = 0;
              stateStore.arq_total_bytes = 0;
            }, 5000);

            return;
        }
      }

      if (data["arq-transfer-inbound"]) {
        stateStore.arq_is_receiving = true;
        switch (data["arq-transfer-inbound"].state) {
          case "NEW":
            message = `
              <div>
                <strong>New transmission with:</strong>
                <span class="badge bg-info text-dark">${data["arq-transfer-inbound"].dxcall}</span>
                <div class="mt-2">
                  <span class="badge bg-secondary">Session ID: ${data["arq-transfer-inbound"].session_id}</span>
                  <span class="badge bg-warning text-dark">Total Bytes: ${data["arq-transfer-inbound"].total_bytes}</span>
                </div>
              </div>
            `;
            displayToast("info", "bi-info-circle", message, 10000);
            stateStore.dxcallsign = data["arq-transfer-inbound"].dxcall;
            stateStore.arq_transmission_percent = 0;
            stateStore.arq_total_bytes = 0;
            return;

          case "OPEN_ACK_SENT":
            message = `
              <div>
                <strong>Confirming transmission with:${data["arq-transfer-inbound"].dxcall}</strong>
                <span class="badge bg-info text-dark">${data["arq-transfer-inbound"].dxcall}</span>
                <div class="mt-2">
                  <span class="badge bg-secondary">Session ID: ${data["arq-transfer-inbound"].session_id}</span>
                  <span class="badge bg-warning text-dark">Received Bytes: ${data["arq-transfer-inbound"].received_bytes}</span>
                  <span class="badge bg-warning text-dark">Total Bytes: ${data["arq-transfer-inbound"].total_bytes}</span>
                </div>
              </div>
            `;
            displayToast("info", "bi-arrow-left-right", message, 5000);
            stateStore.arq_transmission_percent = Math.round(
              (data["arq-transfer-inbound"].received_bytes /
                data["arq-transfer-inbound"].total_bytes) *
              100);
            stateStore.arq_total_bytes =
              data["arq-transfer-inbound"].received_bytes;
            return;

          case "INFO_ACK_SENT":
            message = `
              <div>
                <strong>opening transmission with:${data["arq-transfer-inbound"].dxcall}</strong>
                <span class="badge bg-info text-dark">${data["arq-transfer-inbound"].dxcall}</span>
                <div class="mt-2">
                  <span class="badge bg-secondary">Session ID: ${data["arq-transfer-inbound"].session_id}</span>
                  <span class="badge bg-warning text-dark">Received Bytes: ${data["arq-transfer-inbound"].received_bytes}</span>
                  <span class="badge bg-warning text-dark">Total Bytes: ${data["arq-transfer-inbound"].total_bytes}</span>
                </div>
              </div>
            `;
            displayToast("info", "bi-info-circle", message, 5000);
            stateStore.arq_transmission_percent = Math.round(
              (data["arq-transfer-inbound"].received_bytes /
                data["arq-transfer-inbound"].total_bytes) *
                100,
            );
            stateStore.arq_total_bytes =
              data["arq-transfer-inbound"].received_bytes;
            return;

          case "BURST_REPLY_SENT":
            message = `
              <div>
                <strong>ongoing transmission with:</strong>
                <span class="badge bg-info text-dark">${data["arq-transfer-inbound"].dxcall}</span>
                <div class="mt-2">
                  <span class="badge bg-secondary">Session ID: ${data["arq-transfer-outbound"].session_id}</span>
                  <span class="badge bg-warning text-dark">Received Bytes: ${data["arq-transfer-outbound"].received_bytes}</span>
                  <span class="badge bg-warning text-dark">Total Bytes: ${data["arq-transfer-outbound"].total_bytes}</span>
                </div>
              </div>
            `;
            displayToast("info", "bi-info-circle", message, 5000);

            stateStore.arq_transmission_percent = Math.round(
              (data["arq-transfer-inbound"].received_bytes /
                data["arq-transfer-inbound"].total_bytes) *
                100,
            );
            stateStore.arq_total_bytes =
              data["arq-transfer-inbound"].received_bytes;
            stateStore.arq_speed_list_timestamp.value = toRaw(
              data["arq-transfer-inbound"].statistics.time_histogram,
            );
            stateStore.arq_speed_list_bpm.value = toRaw(
              data["arq-transfer-inbound"].statistics.bpm_histogram,
            );
            stateStore.arq_speed_list_snr.value = toRaw(
              data["arq-transfer-inbound"].statistics.snr_histogram,
            );
            stateStore.speed_level = data["arq-transfer-inbound"].speed_level;
            return;

          case "ENDED":
            message = `
              <div>
                <strong>transmission ENDED with:</strong>
                <span class="badge bg-info text-dark">${data["arq-transfer-inbound"].dxcall}</span>
                <div class="mt-2">
                  <span class="badge bg-primary">STATE: ${data["arq-transfer-inbound"].state}</span>
                  <span class="badge bg-secondary">Session ID: ${data["arq-transfer-inbound"].session_id}</span>
                  <span class="badge bg-warning text-dark">Received Bytes: ${data["arq-transfer-inbound"].received_bytes}</span>
                  <span class="badge bg-warning text-dark">Total Bytes: ${data["arq-transfer-inbound"].total_bytes}</span>
                </div>
              </div>
            `;

            displayToast("info", "bi-info-circle", message, 5000);
            //newMessageReceived(
            //  data["arq-transfer-inbound"].data,
            //  data["arq-transfer-inbound"]
            //);
            stateStore.arq_transmission_percent = Math.round(
              (data["arq-transfer-inbound"].received_bytes /
                data["arq-transfer-inbound"].total_bytes) *
              100);
            stateStore.arq_total_bytes =
              data["arq-transfer-inbound"].received_bytes;

            // Reset progressbar values after a delay
            setTimeout(() => {
              stateStore.arq_transmission_percent = 0;
              stateStore.arq_total_bytes = 0;
            }, 5000);
            return;

          case "ABORTED":
            message = `
              <div>
                <strong>transmission ABORTED with:</strong>
                <span class="badge bg-info text-dark">${data["arq-transfer-inbound"].dxcall}</span>
                <div class="mt-2">
                  <span class="badge bg-primary">STATE: ${data["arq-transfer-inbound"].state}</span>
                  <span class="badge bg-secondary">Session ID: ${data["arq-transfer-inbound"].session_id}</span>
                  <span class="badge bg-warning text-dark">Received Bytes: ${data["arq-transfer-inbound"].received_bytes}</span>
                  <span class="badge bg-warning text-dark">Total Bytes: ${data["arq-transfer-inbound"].total_bytes}</span>
                </div>
              </div>
            `;
            displayToast("danger", "bi-x-octagon", message, 5000);
            stateStore.arq_transmission_percent = 0;
            stateStore.arq_total_bytes = 0;
            return;

          case "FAILED":
            message = `
              <div>
                <strong>transmission FAILED with:</strong>
                <span class="badge bg-info text-dark">${data["arq-transfer-inbound"].dxcall}</span>
                <div class="mt-2">
                  <span class="badge bg-primary">STATE: ${data["arq-transfer-inbound"].state}</span>
                  <span class="badge bg-secondary">Session ID: ${data["arq-transfer-inbound"].session_id}</span>
                  <span class="badge bg-warning text-dark">Received Bytes: ${data["arq-transfer-inbound"].received_bytes}</span>
                  <span class="badge bg-warning text-dark">Total Bytes: ${data["arq-transfer-inbound"].total_bytes}</span>
                </div>
              </div>
            `;
            displayToast("danger", "bi-x-octagon", message, 5000);
            // Reset progressbar values after a delay
            setTimeout(() => {
              stateStore.arq_transmission_percent = 0;
              stateStore.arq_total_bytes = 0;
            }, 5000);
            return;
        }
      }
      return;
  }
}

function build_HSL() {
  for (let i = 0; i < stateStore.activities.length; i++) {
    if (
      stateStore.activities[i][1].direction !== "received" ||
      stateStore.activities[i][1].origin === undefined
    ) {
      continue;
    }
    let found = false;
    for (let ii = 0; ii < stateStore.heard_stations.length; ii++) {
      if (
        stateStore.heard_stations[ii].origin ===
        stateStore.activities[i][1].origin
      ) {
        found = true;
        if (
          stateStore.heard_stations[ii].timestamp <
          stateStore.activities[i][1].timestamp
        ) {
          stateStore.heard_stations[ii] = stateStore.activities[i][1];
        }
      }
    }
    if (!found) {
      stateStore.heard_stations.push(stateStore.activities[i][1]);
    }
  }
  stateStore.heard_stations.sort((a, b) => b.timestamp - a.timestamp);
}

export function getOverallHealth() {
  let health = 0;
  if (stateStore.modem_connection !== "connected") {
    health += 5;
    stateStore.is_modem_running = false;
    stateStore.radio_status = false;
  }
  if (!stateStore.is_modem_running) health += 3;
  if (stateStore.radio_status === false) health += 2;
  if (process.env.FDUpdateAvail === "1") health += 1;
  return health;
}

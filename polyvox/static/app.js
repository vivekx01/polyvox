(function () {
  const form = document.getElementById("generate-form");
  if (!form) return;

  const submitBtn = document.getElementById("submit-btn");
  const message = document.getElementById("form-message");
  const rows = document.getElementById("job-rows");
  const SPINNER = '<span class="spinner spinner-dark"></span>';

  function statusBadge(status) {
    return `<span class="badge badge-${status}"><span class="badge-dot"></span>${status}</span>`;
  }

  function audioCell(job) {
    if (job.status === "finished" && job.audio_url) {
      return `
        <div class="flex items-center gap-2">
          <audio controls preload="none" class="h-8 max-w-[170px] sm:max-w-[220px]" src="${job.audio_url}"></audio>
          <a class="text-indigo-600 hover:underline text-xs font-medium shrink-0" href="${job.audio_url}" download>Download</a>
        </div>
      `;
    }
    if (job.status === "failed") {
      return `<span class="text-red-600 text-xs">${job.error || "failed"}</span>`;
    }
    return '<span class="text-slate-300">&mdash;</span>';
  }

  function upsertRow(job, textPreview, lang) {
    let row = rows.querySelector(`tr[data-job-id="${job.job_id}"]`);
    if (!row) {
      row = document.createElement("tr");
      row.dataset.jobId = job.job_id;
      row.className = "border-b border-slate-100 last:border-0";
      row.innerHTML = `
        <td class="px-4 py-3 max-w-xs truncate"></td>
        <td class="px-4 py-3 text-slate-500"></td>
        <td class="px-4 py-3 job-status"></td>
        <td class="px-4 py-3 job-audio"></td>
        <td class="px-4 py-3 text-right">
          <button type="button" class="delete-job-btn btn-danger-text">Delete</button>
        </td>
      `;
      rows.prepend(row);
      row.children[0].textContent = textPreview;
      row.children[1].textContent = lang;
    }
    row.querySelector(".job-status").innerHTML = statusBadge(job.status);
    row.querySelector(".job-audio").innerHTML = audioCell(job);
  }

  function pollJob(jobId, textPreview, lang) {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/v1/jobs/${jobId}`, { credentials: "same-origin" });
        if (!res.ok) {
          clearInterval(interval);
          return;
        }
        const job = await res.json();
        upsertRow(job, textPreview, lang);
        if (job.status === "finished" || job.status === "failed" || job.status === "expired") {
          clearInterval(interval);
        }
      } catch (err) {
        clearInterval(interval);
      }
    }, 2000);
  }

  // Resume polling for any jobs still in progress on initial page load.
  rows.querySelectorAll("tr[data-job-id]").forEach((row) => {
    const statusText = row.querySelector(".job-status").textContent.trim();
    if (statusText === "queued" || statusText === "started") {
      const textPreview = row.children[0].textContent;
      const lang = row.children[1].textContent;
      pollJob(row.dataset.jobId, textPreview, lang);
    }
  });

  rows.addEventListener("click", async (event) => {
    if (!event.target.classList.contains("delete-job-btn")) return;
    const row = event.target.closest("tr[data-job-id]");
    if (!row) return;

    const btn = event.target;
    btn.disabled = true;
    const originalHtml = btn.innerHTML;
    btn.innerHTML = SPINNER;
    try {
      const res = await fetch(`/api/v1/jobs/${row.dataset.jobId}`, {
        method: "DELETE",
        credentials: "same-origin",
      });
      if (res.ok || res.status === 404) {
        row.remove();
      } else {
        btn.disabled = false;
        btn.innerHTML = originalHtml;
      }
    } catch (err) {
      btn.disabled = false;
      btn.innerHTML = originalHtml;
    }
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const originalBtnHtml = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = `${SPINNER.replace("spinner-dark", "")} Generating…`;
    message.textContent = "";

    const text = document.getElementById("text").value;
    const lang = document.getElementById("lang").value;
    const payload = {
      text,
      lang,
      voice: document.getElementById("voice").value,
      speed: parseFloat(document.getElementById("speed").value),
      steps: parseInt(document.getElementById("steps").value, 10),
    };

    try {
      const res = await fetch("/api/v1/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        message.textContent = "Error: " + (err.detail ? JSON.stringify(err.detail) : res.statusText);
        return;
      }

      const job = await res.json();
      message.textContent = "Queued.";
      upsertRow(
        { job_id: job.job_id, status: job.status, audio_url: null, error: null },
        text.slice(0, 200),
        lang
      );
      pollJob(job.job_id, text.slice(0, 200), lang);
      form.reset();
    } catch (err) {
      message.textContent = "Request failed.";
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalBtnHtml;
    }
  });
})();

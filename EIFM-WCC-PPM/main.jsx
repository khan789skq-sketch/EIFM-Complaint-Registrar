import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { auth, firebaseConfigured } from "./firebase";
import {
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  sendPasswordResetEmail,
  signOut,
  onAuthStateChanged
} from "firebase/auth";
import {
  buildings,
  equipmentSheets,
  clientDefault,
  checklistHeaders,
  documents
} from "./data";
import * as XLSX from "xlsx";
import jsPDF from "jspdf";
import "./styles.css";

const key = (uid) => `eifm_records_${uid || "demo"}`;

const load = (uid) => {
  try {
    return JSON.parse(localStorage.getItem(key(uid)) || "[]");
  } catch {
    return [];
  }
};

/* ---------------- AUTH ---------------- */

function Auth({ onUser }) {
  const [mode, setMode] = useState("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setErr("");

    if (!firebaseConfigured) {
      onUser({
        uid: "demo",
        email: email || "demo@eifm.local"
      });
      return;
    }

    try {
      const r =
        mode === "signup"
          ? await createUserWithEmailAndPassword(auth, email, password)
          : await signInWithEmailAndPassword(auth, email, password);

      onUser(r.user);
    } catch (x) {
      setErr(x.message);
    }
  };

  const reset = async () => {
    if (!email) {
      setErr("Enter your email first.");
      return;
    }

    if (!firebaseConfigured) {
      setErr("Password reset requires Firebase configuration.");
      return;
    }

    try {
      await sendPasswordResetEmail(auth, email);
      setErr("Password reset email sent.");
    } catch (x) {
      setErr(x.message);
    }
  };

  return (
    <div className="auth">
      <div className="authcard">
        <div className="logo">
          <div className="mark">⌂</div>
          <b>EIFM</b>
          <small>إيفم</small>
        </div>

        <h1>{mode === "signin" ? "Login" : "Create Account"}</h1>
        <p>Welcome to EIFM WCC & PPM</p>

        <form onSubmit={submit}>
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength="6"
          />

          {err && <div className="error">{err}</div>}

          <button className="primary">
            {mode === "signin" ? "Sign In" : "Sign Up"}
          </button>
        </form>

        {mode === "signin" && (
          <button className="link" onClick={reset}>
            Forgot Password?
          </button>
        )}

        <div className="or">or</div>

        <button
          className="link"
          onClick={() => {
            setErr("");
            setMode(mode === "signin" ? "signup" : "signin");
          }}
        >
          {mode === "signin"
            ? "Don't have an account? Sign Up"
            : "Already have an account? Sign In"}
        </button>
      </div>
    </div>
  );
}

/* ---------------- SIGNATURE PAD ---------------- */

function SignaturePad({ value, onChange, title }) {
  const canvasRef = useRef(null);
  const drawing = useRef(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (value) {
      const img = new Image();

      img.onload = () => {
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      };

      img.src = value;
    }
  }, [value]);

  const position = (e) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();

    const point =
      e.touches && e.touches.length
        ? e.touches[0]
        : e;

    return {
      x: ((point.clientX - rect.left) / rect.width) * canvas.width,
      y: ((point.clientY - rect.top) / rect.height) * canvas.height
    };
  };

  const start = (e) => {
    e.preventDefault();

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    const p = position(e);

    drawing.current = true;

    ctx.beginPath();
    ctx.moveTo(p.x, p.y);
  };

  const move = (e) => {
    if (!drawing.current) return;

    e.preventDefault();

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    const p = position(e);

    ctx.lineWidth = 2;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    ctx.lineTo(p.x, p.y);
    ctx.stroke();
  };

  const end = () => {
    if (!drawing.current) return;

    drawing.current = false;

    const canvas = canvasRef.current;
    onChange(canvas.toDataURL("image/png"));
  };

  const clear = () => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    onChange("");
  };

  return (
    <div className="signaturebox">
      <div className="signaturetitle">{title}</div>

      <canvas
        ref={canvasRef}
        width={700}
        height={180}
        className="signaturecanvas"
        onMouseDown={start}
        onMouseMove={move}
        onMouseUp={end}
        onMouseLeave={end}
        onTouchStart={start}
        onTouchMove={move}
        onTouchEnd={end}
      />

      <button type="button" className="small" onClick={clear}>
        Clear Signature
      </button>
    </div>
  );
}

/* ---------------- CHECKLIST ---------------- */

function Checklist({ items, setItems }) {
  const add = () =>
    setItems([
      ...items,
      {
        id: Date.now() + Math.random(),
        task: "",
        ok: false,
        notOk: false,
        remarks: "",
        follow: ""
      }
    ]);

  const update = (id, changes) => {
    setItems(
      items.map((x) =>
        x.id === id ? { ...x, ...changes } : x
      )
    );
  };

  return (
    <div>
      <div className="rowbetween">
        <h3>Checklist</h3>

        <button type="button" className="small" onClick={add}>
          + Add Task
        </button>
      </div>

      <div className="tablewrap">
        <table>
          <thead>
            <tr>
              {checklistHeaders.map((h) => (
                <th key={h}>{h}</th>
              ))}
            </tr>
          </thead>

          <tbody>
            {items.map((r, i) => (
              <tr key={r.id}>
                <td>{i + 1}</td>

                <td>
                  <input
                    value={r.task}
                    onChange={(e) =>
                      update(r.id, {
                        task: e.target.value
                      })
                    }
                  />
                </td>

                <td>
                  <input
                    type="checkbox"
                    checked={!!r.ok}
                    onChange={(e) =>
                      update(r.id, {
                        ok: e.target.checked,
                        notOk: false
                      })
                    }
                  />
                </td>

                <td>
                  <input
                    type="checkbox"
                    checked={!!r.notOk}
                    onChange={(e) =>
                      update(r.id, {
                        notOk: e.target.checked,
                        ok: false
                      })
                    }
                  />
                </td>

                <td>
                  <input
                    value={r.remarks}
                    onChange={(e) =>
                      update(r.id, {
                        remarks: e.target.value
                      })
                    }
                  />
                </td>

                <td>
                  <input
                    value={r.follow}
                    onChange={(e) =>
                      update(r.id, {
                        follow: e.target.value
                      })
                    }
                  />
                </td>
              </tr>
            ))}

            {!items.length && (
              <tr>
                <td colSpan={6}>
                  No checklist task added. Click "+ Add Task".
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ---------------- MAIN APP ---------------- */

function App({ user }) {
  const [type, setType] = useState("WCC");

  const [records, setRecords] = useState(() =>
    load(user.uid)
  );

  const [building, setBuilding] = useState("");
  const [project, setProject] = useState("");
  const [client, setClient] = useState(clientDefault);
  const [wo, setWo] = useState("");
  const [ppm, setPpm] = useState("1st PPM");
  const [tel, setTel] = useState("");
  const [details, setDetails] = useState("");
  const [date, setDate] = useState("");

  const [equipment, setEquipment] = useState([]);
  const [checklists, setChecklists] = useState({});

  const [documentsChecked, setDocumentsChecked] = useState([]);
  const [satisfaction, setSatisfaction] = useState("");
  const [remarks, setRemarks] = useState("");

  const [siteSignature, setSiteSignature] = useState("");
  const [hodSignature, setHodSignature] = useState("");
  const [clientSignature, setClientSignature] = useState("");

  const [view, setView] = useState("new");
  const [search, setSearch] = useState("");

  useEffect(() => {
    localStorage.setItem(
      key(user.uid),
      JSON.stringify(records)
    );
  }, [records, user.uid]);

  const selected = equipment.map((e) => ({
    name: e,
    rows: checklists[e] || []
  }));

  const toggleEquipment = (e) => {
    setEquipment((current) =>
      current.includes(e)
        ? current.filter((x) => x !== e)
        : [...current, e]
    );

    if (!checklists[e]) {
      setChecklists((current) => ({
        ...current,
        [e]: []
      }));
    }
  };

  const toggleDocument = (doc) => {
    setDocumentsChecked((current) =>
      current.includes(doc)
        ? current.filter((x) => x !== doc)
        : [...current, doc]
    );
  };

  const resetForm = () => {
    setBuilding("");
    setProject("");
    setClient(clientDefault);
    setWo("");
    setPpm("1st PPM");
    setTel("");
    setDetails("");
    setDate("");
    setEquipment([]);
    setChecklists({});
    setDocumentsChecked([]);
    setSatisfaction("");
    setRemarks("");
    setSiteSignature("");
    setHodSignature("");
    setClientSignature("");
  };

  const save = () => {
    if (!building) {
      alert("Please select Building / Location.");
      return;
    }

    if (type === "WCC" && !wo) {
      alert("Please enter Work Order Number.");
      return;
    }

    if (type === "PPM" && !ppm) {
      alert("Please select PPM.");
      return;
    }

    const r = {
      id: Date.now(),
      type,
      building,
      project,
      client,
      wo,
      ppm,
      tel,
      details,
      date,
      equipment,
      checklists,
      documentsChecked,
      satisfaction,
      remarks,
      siteSignature,
      hodSignature,
      clientSignature,
      createdAt: new Date().toISOString()
    };

    setRecords((current) => [r, ...current]);

    alert(`${type} saved successfully.`);

    setView("records");
  };

  /* ---------------- EXCEL EXPORT ---------------- */

  const exportX = () => {
    if (!records.length) {
      alert("No saved records available.");
      return;
    }

    const rows = [];

    records.forEach((r) => {
      rows.push({
        Type: r.type,
        Building: r.building,
        Client: r.client,
        Project: r.project,
        "WO Number": r.wo,
        PPM: r.ppm,
        "Tel. No.": r.tel,
        "Date & Time": r.date,
        Details: r.details,
        Equipment: (r.equipment || []).join(", "),
        "Enclosed Documents": (r.documentsChecked || []).join(", "),
        Satisfaction: r.satisfaction,
        "Remarks / Suggestions": r.remarks,
        "Created At": r.createdAt
      });
    });

    const checklistRows = [];

    records.forEach((r) => {
      Object.entries(r.checklists || {}).forEach(
        ([equipmentName, rowsList]) => {
          rowsList.forEach((x, i) => {
            checklistRows.push({
              RecordID: r.id,
              Type: r.type,
              Building: r.building,
              Equipment: equipmentName,
              "S.No": i + 1,
              Task: x.task,
              Status: x.ok
                ? "OK"
                : x.notOk
                ? "NOT OK"
                : "",
              Remarks: x.remarks,
              "Follow Up": x.follow
            });
          });
        }
      );
    });

    const wb = XLSX.utils.book_new();

    XLSX.utils.book_append_sheet(
      wb,
      XLSX.utils.json_to_sheet(rows),
      "Records"
    );

    if (checklistRows.length) {
      XLSX.utils.book_append_sheet(
        wb,
        XLSX.utils.json_to_sheet(checklistRows),
        "Checklists"
      );
    }

    XLSX.writeFile(
      wb,
      "EIFM-WCC-PPM-Records.xlsx"
    );
  };

  /* ---------------- PDF EXPORT ---------------- */

  const pdf = (record = null) => {
    const r = record || {
      type,
      building,
      project,
      client,
      wo,
      ppm,
      tel,
      details,
      date,
      equipment,
      checklists,
      documentsChecked,
      satisfaction,
      remarks,
      siteSignature,
      hodSignature,
      clientSignature
    };

    const d = new jsPDF();

    const title =
      r.type === "WCC"
        ? "WORK COMPLETION CERTIFICATE"
        : "PLANNED PREVENTIVE MAINTENANCE";

    d.setFontSize(16);
    d.text(title, 15, 18);

    d.setFontSize(10);

    let y = 30;

    const basic = [
      [
        r.type === "WCC"
          ? "Job Order Number"
          : "PPM Number",
        r.type === "WCC" ? r.wo : r.ppm
      ],
      ["Client", r.client],
      ["Project", r.project],
      ["Location", r.building],
      ["Tel. No.", r.tel],
      ["Date & Time", r.date]
    ];

    basic.forEach(([a, b]) => {
      d.text(
        `${a}: ${b || ""}`,
        15,
        y
      );
      y += 7;
    });

    if (r.details) {
      y += 3;

      d.setFontSize(12);
      d.text("Details / Work Description", 15, y);

      y += 7;

      d.setFontSize(9);

      const detailLines = d.splitTextToSize(
        r.details,
        175
      );

      detailLines.forEach((line) => {
        if (y > 275) {
          d.addPage();
          y = 20;
        }

        d.text(line, 15, y);
        y += 5;
      });
    }

    y += 5;

    d.setFontSize(12);
    d.text("Equipment / Checklist", 15, y);

    y += 7;

    d.setFontSize(9);

    selectedFromRecord(r).forEach((s) => {
      if (y > 270) {
        d.addPage();
        y = 20;
      }

      d.setFontSize(10);
      d.text(s.name, 15, y);
      y += 6;

      d.setFontSize(8);

      s.rows.forEach((x, i) => {
        if (y > 275) {
          d.addPage();
          y = 20;
        }

        const status = x.ok
          ? "OK"
          : x.notOk
          ? "NOT OK"
          : "";

        const text = `${i + 1}. ${x.task || ""} | ${status} | ${
          x.remarks || ""
        } | ${x.follow || ""}`;

        const lines = d.splitTextToSize(
          text,
          175
        );

        lines.forEach((line) => {
          if (y > 275) {
            d.addPage();
            y = 20;
          }

          d.text(line, 18, y);
          y += 4;
        });
      });

      y += 3;
    });

    if (r.type === "WCC") {
      if (y > 245) {
        d.addPage();
        y = 20;
      }

      d.setFontSize(11);
      d.text("Enclosed Documents", 15, y);

      y += 6;

      d.setFontSize(9);

      (r.documentsChecked || []).forEach((doc) => {
        d.text(`✓ ${doc}`, 18, y);
        y += 5;
      });

      y += 5;

      d.text(
        `Customer Satisfaction: ${
          r.satisfaction || "Not selected"
        }`,
        15,
        y
      );

      y += 6;

      if (r.remarks) {
        d.text(
          `Remarks / Suggestions: ${r.remarks}`,
          15,
          y
        );
        y += 7;
      }
    }

    /* SIGNATURES */

    if (y > 215) {
      d.addPage();
      y = 20;
    }

    d.setFontSize(11);
    d.text("Signatures", 15, y);

    y += 8;

    const signatures = [
      ["Site In Charge", r.siteSignature],
      ["HOD", r.hodSignature],
      ["Client", r.clientSignature]
    ];

    signatures.forEach(([name, signature]) => {
      if (y > 245) {
        d.addPage();
        y = 20;
      }

      d.setFontSize(9);
      d.text(name, 15, y);

      y += 4;

      if (signature) {
        try {
          d.addImage(
            signature,
            "PNG",
            15,
            y,
            70,
            18
          );
        } catch {
          d.text(
            "Signature available",
            15,
            y + 8
          );
        }
      } else {
        d.line(15, y + 15, 85, y + 15);
      }

      y += 24;
    });

    d.save(
      `${r.type}-${r.building || "record"}.pdf`
    );
  };

  const filtered = useMemo(
    () =>
      records.filter((r) =>
        JSON.stringify(r)
          .toLowerCase()
          .includes(search.toLowerCase())
      ),
    [records, search]
  );

  return (
    <div className="app">
      <header>
        <div className="brand">
          <span className="mark">⌂</span>
          <b>EIFM</b>
        </div>

        <nav>
          <button
            className={view === "new" ? "active" : ""}
            onClick={() => setView("new")}
          >
            New
          </button>

          <button
            className={
              view === "records" ? "active" : ""
            }
            onClick={() => setView("records")}
          >
            Saved Records
          </button>
        </nav>

        <div>
          <span className="email">
            {user.email}
          </span>

          <button
            className="logout"
            onClick={() =>
              firebaseConfigured
                ? signOut(auth)
                : location.reload()
            }
          >
            Sign Out
          </button>
        </div>
      </header>

      {view === "records" ? (
        <main>
          <div className="rowbetween">
            <h2>Saved WCC & PPM Records</h2>

            <div>
              <button
                className="small"
                onClick={exportX}
              >
                Export Excel
              </button>

              <button
                className="small"
                onClick={() => {
                  setView("new");
                  resetForm();
                }}
              >
                New Record
              </button>
            </div>
          </div>

          <input
            placeholder="Search building, WO, client..."
            value={search}
            onChange={(e) =>
              setSearch(e.target.value)
            }
          />

          <div className="cards">
            {filtered.map((r) => (
              <div
                className="record"
                key={r.id}
              >
                <b>
                  {r.type} — {r.building}
                </b>

                <p>
                  Client: {r.client}
                </p>

                <p>
                  Project: {r.project || "—"}
                </p>

                <p>
                  {r.type === "PPM"
                    ? r.ppm
                    : `WO: ${r.wo}`}
                </p>

                <p>
                  Tel: {r.tel || "—"}
                </p>

                <p>
  Equipment: {r.equipment || "—"}
</p>
  
  

</div>
))}
</div>
  





                
       

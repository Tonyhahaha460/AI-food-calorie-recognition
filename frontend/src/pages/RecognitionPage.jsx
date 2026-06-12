import { useEffect, useMemo, useRef, useState } from "react";
import { fetchFoodProfiles, uploadTrainingFeedback } from "../api/foodProfilesApi";
import { predictMeal } from "../api/predictionApi";
import Layout from "../components/Layout";
import MealResults from "../components/MealResults";
import TodayJournalSection from "../components/TodayJournalSection";
import UploadPanel from "../components/UploadPanel";
import { useAuth } from "../context/AuthContext";
import {
  addJournalEntry,
  buildJournalDateTimePayload,
  getLocalDateTimeInputValue,
  listTodayJournalEntries,
  normalizeNutrition,
  removeJournalEntry,
  summarizeTodayJournal,
} from "../utils/memberJournal";

const MAX_FILE_SIZE = 4 * 1024 * 1024;

const COPY = {
  loadFoodProfilesFailed: "無法載入食物資料庫，請稍後再試。",
  invalidImageType: "請上傳 JPG 或 PNG 圖片。",
  fileTooLarge: "圖片太大，請選擇 4 MB 以內的檔案。",
  fileRequired: "請先選擇一張餐點圖片。",
  loginPrompt: "請先登入會員，才能加入今日飲食紀錄。",
  missingEntry: "目前沒有可加入紀錄的餐點，請先完成 AI 分析或手動查詢。",
  addJournalFailed: "加入今日飲食紀錄失敗，請稍後再試。",
  removeJournalFailed: "刪除今日飲食紀錄失敗，請稍後再試。",
};

function buildManualResult(manualLookup) {
  if (!manualLookup) {
    return null;
  }

  return {
    food_name: manualLookup.foodName,
    portion_label: manualLookup.portionLabel,
    nutrition: normalizeNutrition(manualLookup),
    image_preview: "",
    source: "manual_lookup",
    recordedDateTime: manualLookup.recordedDateTime,
    localDateTime: manualLookup.recordedDateTime,
    local_date_time: manualLookup.recordedDateTime,
    date: manualLookup.recordedDateTime ? manualLookup.recordedDateTime.slice(0, 10) : "",
    local_date: manualLookup.recordedDateTime ? manualLookup.recordedDateTime.slice(0, 10) : "",
    date_key: manualLookup.recordedDateTime ? manualLookup.recordedDateTime.slice(0, 10) : "",
    recorded_at: manualLookup.recordedAt,
    history_record_id: null,
  };
}

function buildAiResult(result, previewUrl) {
  if (!result || !result.items || result.items.length === 0) {
    return null;
  }

  const combinedName =
    result.items.length === 1
      ? result.items[0].food_name
      : result.items.map((item) => item.food_name).join(" + ");

  const portionLabel =
    result.items.length === 1 ? result.items[0].estimated_portion : `${result.items.length} 個項目`;

  return {
    food_name: combinedName,
    portion_label: portionLabel,
    nutrition: normalizeNutrition({
      ...result,
      nutrition: result.total_nutrition,
      total_calories: result.total_calories,
    }),
    image_preview: result.image_preview || previewUrl,
    source: result.analysis_mode || "ai",
    history_record_id: result.history_record_id || null,
  };
}

function RecognitionPage() {
  const { isMemberLoggedIn, memberAccount, openAuthModal } = useAuth();
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [foodProfiles, setFoodProfiles] = useState([]);
  const [foodProfilesLoading, setFoodProfilesLoading] = useState(true);
  const [foodProfilesError, setFoodProfilesError] = useState("");
  const [manualLookup, setManualLookup] = useState(null);
  const [appliedManualLookup, setAppliedManualLookup] = useState(null);
  const [todayEntries, setTodayEntries] = useState([]);
  const [journalSourceMode, setJournalSourceMode] = useState("");
  const [logDateTime, setLogDateTime] = useState(() => getLocalDateTimeInputValue());
  const savedFeedbackKeysRef = useRef(new Set());

  const manualCandidate = useMemo(
    () => buildManualResult(manualLookup || appliedManualLookup),
    [appliedManualLookup, manualLookup]
  );

  const aiCandidate = useMemo(() => buildAiResult(result, previewUrl), [previewUrl, result]);

  const journalCandidate = useMemo(() => {
    if (journalSourceMode === "manual" && manualCandidate) {
      return manualCandidate;
    }
    if (journalSourceMode === "ai" && aiCandidate) {
      return aiCandidate;
    }
    return aiCandidate || manualCandidate || null;
  }, [aiCandidate, journalSourceMode, manualCandidate]);

  const journalSummary = useMemo(
    () =>
      isMemberLoggedIn
        ? summarizeTodayJournal(todayEntries)
        : { count: 0, calories: 0, protein: 0, fat: 0, carbs: 0 },
    [isMemberLoggedIn, todayEntries]
  );

  useEffect(() => {
    loadFoodProfiles();
  }, []);

  useEffect(() => {
    syncTodayEntries();
  }, [isMemberLoggedIn, memberAccount]);

  useEffect(() => {
    if (manualCandidate?.recordedDateTime) {
      setLogDateTime(manualCandidate.recordedDateTime);
    }
  }, [manualCandidate?.recordedDateTime]);

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  async function syncTodayEntries() {
    if (!isMemberLoggedIn) {
      setTodayEntries([]);
      return;
    }

    try {
      const entries = await listTodayJournalEntries(memberAccount);
      setTodayEntries(entries);
    } catch {
      setTodayEntries([]);
    }
  }

  async function loadFoodProfiles() {
    setFoodProfilesLoading(true);
    setFoodProfilesError("");

    try {
      const items = await fetchFoodProfiles();
      setFoodProfiles(items);
    } catch (requestError) {
      setFoodProfiles([]);
      setFoodProfilesError(requestError.message || COPY.loadFoodProfilesFailed);
    } finally {
      setFoodProfilesLoading(false);
    }
  }

  function handleFileChange(event) {
    const file = event.target.files?.[0];

    setError("");
    setAppliedManualLookup(null);
    savedFeedbackKeysRef.current.clear();

    if (!file) {
      setSelectedFile(null);
      setPreviewUrl("");
      return;
    }

    if (!["image/jpeg", "image/png"].includes(file.type)) {
      setError(COPY.invalidImageType);
      setSelectedFile(null);
      setPreviewUrl("");
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setError(COPY.fileTooLarge);
      setSelectedFile(null);
      setPreviewUrl("");
      return;
    }

    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }

    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
  }

  async function handleSubmit() {
    if (!selectedFile) {
      setError(COPY.fileRequired);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const prediction = await predictMeal(selectedFile);
      setResult(prediction);
      setJournalSourceMode("ai");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  function handleManualLookupChange(selection) {
    setManualLookup(selection);

    if (selection) {
      setJournalSourceMode("manual");
    } else if (result) {
      setJournalSourceMode("ai");
    } else {
      setJournalSourceMode("");
    }

    setAppliedManualLookup((current) => {
      if (!current) {
        return current;
      }

      if (!selection) {
        return null;
      }

      if (
        current.label === selection.label &&
        current.portionLabel === selection.portionLabel &&
        current.recordedAt === selection.recordedAt
      ) {
        return selection;
      }

      return current;
    });
  }

  function handleApplyManualLookup(selection) {
    if (!selection) {
      return;
    }

    setAppliedManualLookup(selection);
    setJournalSourceMode("manual");
    void saveManualTrainingFeedback(selection);
  }

  function handleClearAppliedManualLookup() {
    setAppliedManualLookup(null);
    if (manualLookup) {
      setJournalSourceMode("manual");
      return;
    }
    if (result) {
      setJournalSourceMode("ai");
      return;
    }
    setJournalSourceMode("");
  }

  function handleSelectJournalSource(mode) {
    if (mode === "ai" && aiCandidate) {
      setJournalSourceMode("ai");
      return;
    }

    if (mode === "manual" && manualCandidate) {
      setJournalSourceMode("manual");
    }
  }

  async function handleAddTodayJournal() {
    if (!isMemberLoggedIn) {
      setError(COPY.loginPrompt);
      openAuthModal("register");
      return;
    }

    if (!journalCandidate) {
      setError(COPY.missingEntry);
      return;
    }

    try {
      await addJournalEntry(memberAccount, {
        ...journalCandidate,
        ...buildJournalDateTimePayload(logDateTime),
      });
      if (journalSourceMode === "manual") {
        await saveManualTrainingFeedback(manualLookup || appliedManualLookup);
      }
      await syncTodayEntries();
      setLogDateTime(getLocalDateTimeInputValue());
      setError("");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : COPY.addJournalFailed);
    }
  }

  async function saveManualTrainingFeedback(selection) {
    if (!selection || !selectedFile) {
      return;
    }

    const label = selection.label || selection.foodName || "";
    const feedbackKey = `${selectedFile.name}:${selectedFile.size}:${label}:${selection.foodName || ""}`;
    if (savedFeedbackKeysRef.current.has(feedbackKey)) {
      return;
    }

    try {
      await uploadTrainingFeedback({
        label,
        foodName: selection.foodName || "",
        image: selectedFile,
      });
      savedFeedbackKeysRef.current.add(feedbackKey);
    } catch (requestError) {
      console.warn("Training feedback image was not saved.", requestError);
    }
  }

  function handlePromptRegister() {
    setError(COPY.loginPrompt);
    openAuthModal("register");
  }

  async function handleRemoveJournalEntry(entryId) {
    if (!isMemberLoggedIn) {
      return;
    }

    try {
      await removeJournalEntry(memberAccount, entryId);
      await syncTodayEntries();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : COPY.removeJournalFailed);
    }
  }

  return (
    <Layout>
      <section className="page-header recognition-hero">
        <div>
          <p className="eyebrow">AI 食物辨識</p>
          <h1>拍下餐點，自動估算熱量與營養</h1>
          <p className="subtitle">
            上傳餐點照片後，系統會辨識食物、估算熱量與蛋白質、脂肪、碳水。若辨識不準，也可以直接用食物資料庫手動修正。
          </p>
          <div className="quest-steps" aria-label="任務流程">
            <span>01 上傳照片</span>
            <span>02 AI 掃描</span>
            <span>03 校正結果</span>
            <span>04 加入日誌</span>
          </div>
        </div>
        <div className="recognition-hero-metrics" aria-label="功能摘要">
          <div>
            <span>模式</span>
            <strong>AI + 手動校正</strong>
          </div>
          <div>
            <span>資料</span>
            <strong>熱量 / 三大營養素</strong>
          </div>
          <div className="threat-meter">
            <span>辨識穩定度</span>
            <strong>ACTIVE</strong>
            <i aria-hidden="true" />
          </div>
        </div>
      </section>

      <div className="workspace-grid recognition-workspace">
        <UploadPanel
          previewUrl={previewUrl}
          selectedFile={selectedFile}
          error={error}
          loading={loading}
          onFileChange={handleFileChange}
          onSubmit={handleSubmit}
          foodProfiles={foodProfiles}
          foodProfilesLoading={foodProfilesLoading}
          foodProfilesError={foodProfilesError}
          onManualLookupChange={handleManualLookupChange}
          appliedManualLookup={appliedManualLookup}
          onApplyManualLookup={handleApplyManualLookup}
          onClearAppliedManualLookup={handleClearAppliedManualLookup}
        />
        <MealResults
          result={result}
          previewUrl={previewUrl}
          manualLookup={manualLookup}
          appliedManualLookup={appliedManualLookup}
        />
      </div>

      <TodayJournalSection
        currentEntry={journalCandidate}
        aiEntry={aiCandidate}
        manualEntry={manualCandidate}
        selectedSourceMode={journalSourceMode}
        onSelectSource={handleSelectJournalSource}
        todayEntries={todayEntries}
        summary={journalSummary}
        logDateTime={logDateTime}
        onLogDateTimeChange={setLogDateTime}
        onAddEntry={handleAddTodayJournal}
        onPromptRegister={handlePromptRegister}
        onRemoveEntry={handleRemoveJournalEntry}
      />
    </Layout>
  );
}

export default RecognitionPage;

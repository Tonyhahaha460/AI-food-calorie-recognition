import { useEffect, useMemo, useState } from "react";
import Layout from "../components/Layout";
import { useAuth } from "../context/AuthContext";
import {
  API_BASE_URL,
  createFoodProfile,
  deleteFoodProfile,
  deleteTrainingImage,
  fetchFoodProfiles,
  fetchTrainingImages,
  trainModel,
  updateFoodProfile,
  uploadTrainingImages,
} from "../api/foodProfilesApi";

const EMPTY_FORM = {
  name: "",
  default_portion_label: "",
  parent_category: "",
  calories: "",
  protein: "",
  fat: "",
  carbs: "",
};

function AdminPage() {
  const { isWorkMode } = useAuth();
  const [items, setItems] = useState([]);
  const [selectedRootLabel, setSelectedRootLabel] = useState("");
  const [selectedLabel, setSelectedLabel] = useState("");
  const [createMode, setCreateMode] = useState("none");
  const [form, setForm] = useState(EMPTY_FORM);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [training, setTraining] = useState(false);
  const [galleryLoading, setGalleryLoading] = useState(false);
  const [galleryFiles, setGalleryFiles] = useState([]);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const roots = useMemo(
    () =>
      items
        .filter((item) => !item.parent_category)
        .sort((a, b) => a.display_name.localeCompare(b.display_name)),
    [items]
  );

  const selectedRoot = useMemo(
    () => roots.find((item) => item.label === selectedRootLabel) || null,
    [roots, selectedRootLabel]
  );

  const childFolders = useMemo(
    () =>
      items
        .filter((item) => item.parent_category === selectedRootLabel)
        .sort((a, b) => a.display_name.localeCompare(b.display_name)),
    [items, selectedRootLabel]
  );

  const selectedItem = useMemo(
    () => items.find((item) => item.label === selectedLabel) || null,
    [items, selectedLabel]
  );

  const selectedPath = useMemo(() => {
    if (!selectedItem) {
      return selectedRootLabel || "";
    }
    return selectedItem.parent_category
      ? `${selectedItem.parent_category} / ${selectedItem.display_name}`
      : selectedItem.display_name;
  }, [selectedItem, selectedRootLabel]);

  useEffect(() => {
    loadProfiles();
  }, []);

  useEffect(() => {
    if (!selectedRootLabel && roots.length) {
      setSelectedRootLabel(roots[0].label);
    }
  }, [roots, selectedRootLabel]);

  useEffect(() => {
    if (!selectedItem) {
      setForm(EMPTY_FORM);
      setGalleryFiles([]);
      return;
    }

    setForm({
      name: selectedItem.display_name,
      default_portion_label: selectedItem.default_portion_label,
      parent_category: selectedItem.parent_category || "",
      calories: String(selectedItem.calories),
      protein: String(selectedItem.protein),
      fat: String(selectedItem.fat),
      carbs: String(selectedItem.carbs),
    });
  }, [selectedItem]);

  useEffect(() => {
    if (!selectedLabel) {
      setGalleryFiles([]);
      return;
    }
    loadGallery(selectedLabel);
  }, [selectedLabel]);

  async function loadProfiles() {
    setLoading(true);
    setError("");
    try {
      const profiles = await fetchFoodProfiles();
      setItems(profiles);
      if (profiles.length > 0 && !selectedRootLabel) {
        const firstRoot = profiles.find((item) => !item.parent_category);
        if (firstRoot) {
          setSelectedRootLabel(firstRoot.label);
        }
      }
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadGallery(label) {
    setGalleryLoading(true);
    try {
      const result = await fetchTrainingImages(label);
      setGalleryFiles(result.files || []);
    } catch {
      setGalleryFiles([]);
    } finally {
      setGalleryLoading(false);
    }
  }

  function rejectVisitor(message) {
    if (!isWorkMode) {
      setError(message);
      return true;
    }
    return false;
  }

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((previous) => ({ ...previous, [name]: value }));
  }

  function openRootFolder(rootLabel) {
    setSelectedRootLabel(rootLabel);
    setSelectedLabel("");
    setCreateMode("none");
    setError("");
    setSuccess("");
  }

  function openChildFolder(label) {
    setSelectedLabel(label);
    setCreateMode("none");
    setError("");
    setSuccess("");
  }

  function startCreateRoot() {
    if (rejectVisitor("目前只有管理員可以建立新的主分類。")) return;
    setSelectedLabel("");
    setCreateMode("root");
    setForm({ ...EMPTY_FORM, parent_category: "" });
    setError("");
    setSuccess("");
  }

  function startCreateSubtype() {
    if (rejectVisitor("目前只有管理員可以建立新的子分類。")) return;
    if (!selectedRootLabel) return;
    setSelectedLabel("");
    setCreateMode("child");
    setForm({ ...EMPTY_FORM, parent_category: selectedRootLabel });
    setError("");
    setSuccess("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (rejectVisitor("目前只有管理員可以儲存資料。")) return;

    setSaving(true);
    setError("");
    setSuccess("");

    try {
      const payload = {
        label: form.name,
        display_name: form.name,
        parent_category: form.parent_category,
        default_portion_label: form.default_portion_label,
        calories: form.calories,
        protein: form.protein,
        fat: form.fat,
        carbs: form.carbs,
      };

      if (selectedLabel) {
        const updated = await updateFoodProfile(selectedLabel, payload);
        setItems((previous) =>
          previous.map((item) => (item.label === selectedLabel ? updated : item))
        );
        setSelectedRootLabel(updated.parent_category || updated.label);
        setSelectedLabel(updated.label);
        setSuccess("食物資料已更新。");
      } else {
        const created = await createFoodProfile(payload);
        setItems((previous) => [...previous, created]);
        setSelectedRootLabel(created.parent_category || created.label);
        setSelectedLabel(created.label);
        setSuccess("新的食物資料已建立。");
      }

      setCreateMode("none");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (rejectVisitor("目前只有管理員可以刪除資料。")) return;
    if (!selectedLabel) return;
    const confirmed = window.confirm(`確定要刪除「${selectedLabel}」嗎？`);
    if (!confirmed) return;

    setSaving(true);
    setError("");
    setSuccess("");

    try {
      await deleteFoodProfile(selectedLabel);
      setItems((previous) => previous.filter((item) => item.label !== selectedLabel));
      setSelectedLabel("");
      setCreateMode("none");
      setSuccess("食物資料已刪除。");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleImageUpload(event) {
    if (rejectVisitor("目前只有管理員可以上傳訓練圖片。")) {
      event.target.value = "";
      return;
    }

    const files = event.target.files;
    if (!selectedLabel || !files?.length) return;

    setUploading(true);
    setError("");
    setSuccess("");

    try {
      const result = await uploadTrainingImages(selectedLabel, files);
      await loadProfiles();
      await loadGallery(selectedLabel);
      setSuccess(`已上傳 ${result.uploaded_count} 張圖片，目前共有 ${result.image_count} 張訓練圖片。`);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  async function handleDeleteImage(filename) {
    if (rejectVisitor("目前只有管理員可以刪除訓練圖片。")) return;
    if (!selectedLabel) return;
    const confirmed = window.confirm(`確定要刪除圖片「${filename}」嗎？`);
    if (!confirmed) return;

    try {
      const result = await deleteTrainingImage(selectedLabel, filename);
      setGalleryFiles(result.files || []);
      await loadProfiles();
      setSuccess("圖片已刪除。");
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function handleTrainModel() {
    if (rejectVisitor("目前只有管理員可以啟動模型訓練。")) return;
    setTraining(true);
    setError("");
    setSuccess("");

    try {
      const result = await trainModel();
      setSuccess(`模型訓練已完成，使用 ${result.image_count} 張圖片、${result.class_count} 個類別。`);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setTraining(false);
    }
  }

  return (
    <Layout>
      <section className="admin-shell">
        <div className="admin-mobile-frame">
          <div className="admin-topbar">
            <div>
              <p className="admin-app-title">管理員模式</p>
              <h1>資料集管理 / 模型訓練</h1>
            </div>

            <div className="topbar-actions">
              <button
                className="primary-button"
                type="button"
                onClick={handleTrainModel}
                disabled={training || !isWorkMode}
              >
                {training ? "訓練中..." : "開始訓練模型"}
              </button>
              <button
                className="secondary-button"
                type="button"
                onClick={startCreateRoot}
                disabled={!isWorkMode}
              >
                新增主分類
              </button>
              <button
                className="secondary-button"
                type="button"
                onClick={startCreateSubtype}
                disabled={!isWorkMode}
              >
                新增子分類
              </button>
            </div>
          </div>

          <div className="folder-browser-grid">
            <aside className="admin-sidebar">
              <div className="admin-section-title">主分類資料夾</div>
              {loading ? <p className="muted-text">載入中...</p> : null}
              {roots.map((root) => (
                <button
                  key={root.label}
                  type="button"
                  className={`root-row ${selectedRootLabel === root.label ? "active" : ""}`}
                  onClick={() => openRootFolder(root.label)}
                >
                  <div>
                    <strong>{root.display_name}</strong>
                    <small>{root.label}</small>
                  </div>
                </button>
              ))}
            </aside>

            <aside className="admin-sidebar second-layer-panel">
              <div className="admin-section-title">子分類資料夾</div>
              {selectedRoot ? (
                <div className="selected-root-label">目前主分類：{selectedRoot.display_name}</div>
              ) : null}
              {childFolders.length === 0 ? (
                <p className="muted-text">這個主分類底下還沒有子分類。</p>
              ) : (
                childFolders.map((item) => (
                  <button
                    key={item.label}
                    type="button"
                    className={`profile-pill child-pill ${selectedLabel === item.label ? "active" : ""}`}
                    onClick={() => openChildFolder(item.label)}
                  >
                    <div>
                      <span>{item.display_name}</span>
                    </div>
                    <small>{item.image_count || 0} 張</small>
                  </button>
                ))
              )}
            </aside>

            <section className="admin-editor-card">
              <div className="admin-section-title">
                {selectedLabel
                  ? "編輯目前食物資料"
                  : createMode === "child"
                    ? "新增子分類食物"
                    : "新增主分類食物"}
              </div>

              {selectedPath ? <div className="path-chip">目前路徑：{selectedPath}</div> : null}
              {error ? <div className="error-banner">{error}</div> : null}
              {success ? <div className="success-banner">{success}</div> : null}

              <form className="admin-form" onSubmit={handleSubmit}>
                <div className="admin-input-row single-column">
                  <label>
                    父分類標籤
                    <input
                      name="parent_category"
                      value={form.parent_category}
                      onChange={handleChange}
                      placeholder="只有建立子分類時需要，主分類請留空"
                      disabled={!isWorkMode || Boolean(selectedItem?.parent_category)}
                    />
                  </label>
                </div>

                <div className="admin-input-row">
                  <label>
                    名稱
                    <input
                      name="name"
                      value={form.name}
                      onChange={handleChange}
                      placeholder={form.parent_category ? "例如：雞肉飯" : "例如：飯類"}
                      disabled={!isWorkMode}
                    />
                  </label>
                  <div />
                </div>

                <div className="admin-input-row">
                  <label>
                    預設份量
                    <input
                      name="default_portion_label"
                      value={form.default_portion_label}
                      onChange={handleChange}
                      placeholder="1 碗"
                      disabled={!isWorkMode}
                    />
                  </label>
                  <div />
                </div>

                <div className="nutrition-admin-grid">
                  <label>
                    Calories
                    <input
                      name="calories"
                      type="number"
                      min="0"
                      step="0.1"
                      value={form.calories}
                      onChange={handleChange}
                      disabled={!isWorkMode}
                    />
                  </label>
                  <label>
                    Protein
                    <input
                      name="protein"
                      type="number"
                      min="0"
                      step="0.1"
                      value={form.protein}
                      onChange={handleChange}
                      disabled={!isWorkMode}
                    />
                  </label>
                  <label>
                    Fat
                    <input
                      name="fat"
                      type="number"
                      min="0"
                      step="0.1"
                      value={form.fat}
                      onChange={handleChange}
                      disabled={!isWorkMode}
                    />
                  </label>
                  <label>
                    Carbs
                    <input
                      name="carbs"
                      type="number"
                      min="0"
                      step="0.1"
                      value={form.carbs}
                      onChange={handleChange}
                      disabled={!isWorkMode}
                    />
                  </label>
                </div>

                {selectedLabel ? (
                  <div className="dataset-card">
                    <div className="dataset-header">
                      <h3>訓練圖片資料</h3>
                    </div>

                    <label className="upload-dropzone dataset-dropzone">
                      <input
                        type="file"
                        accept=".jpg,.jpeg,.png,image/png,image/jpeg"
                        multiple
                        onChange={handleImageUpload}
                        disabled={!isWorkMode}
                      />
                      <span>{uploading ? "上傳中..." : "上傳訓練圖片"}</span>
                      <small>圖片會存到這個食物分類底下，之後可用來補充訓練資料。</small>
                    </label>

                    <div className="gallery-section">
                      <div className="gallery-title">已上傳圖片</div>
                      {galleryLoading ? (
                        <p className="muted-text">載入圖片中...</p>
                      ) : galleryFiles.length === 0 ? (
                        <p className="muted-text">目前還沒有已上傳圖片。</p>
                      ) : (
                        <div className="gallery-grid">
                          {galleryFiles.map((filename) => {
                            const imageUrl = `${API_BASE_URL}/api/food-profiles/${encodeURIComponent(
                              selectedLabel
                            )}/images/${encodeURIComponent(filename)}`;

                            return (
                              <article key={filename} className="gallery-card">
                                <a href={imageUrl} target="_blank" rel="noreferrer" className="gallery-thumb">
                                  <img src={imageUrl} alt={filename} className="preview-image" />
                                </a>
                                <div className="gallery-meta">
                                  <small>{filename}</small>
                                  <div className="gallery-actions">
                                    <a
                                      href={imageUrl}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="secondary-button small-button"
                                    >
                                      檢視
                                    </a>
                                    <button
                                      type="button"
                                      className="danger-button small-button"
                                      onClick={() => handleDeleteImage(filename)}
                                      disabled={!isWorkMode}
                                    >
                                      刪除
                                    </button>
                                  </div>
                                </div>
                              </article>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                ) : null}

                <div className="admin-actions">
                  <button className="primary-button full-width" type="submit" disabled={saving || !isWorkMode}>
                    {isWorkMode
                      ? saving
                        ? "儲存中..."
                        : selectedLabel
                          ? "更新食物資料"
                          : "建立食物資料"
                      : "只有管理員可以操作"}
                  </button>

                  {selectedLabel ? (
                    <button
                      className="danger-button full-width"
                      type="button"
                      onClick={handleDelete}
                      disabled={saving || !isWorkMode}
                    >
                      刪除這筆食物
                    </button>
                  ) : null}
                </div>
              </form>
            </section>
          </div>
        </div>
      </section>
    </Layout>
  );
}

export default AdminPage;

import ManualNutritionLookup from "./ManualNutritionLookup";
import { useState } from "react";

const COPY = {
  analysis: "\u4e0a\u50b3\u5206\u6790",
  title: "\u4e0a\u50b3\u6216\u62d6\u66f3\u9910\u9ede\u7167\u7247",
  chooseImage: "\u9078\u64c7 JPG \u6216 PNG \u98df\u7269\u5716\u7247",
  uploadHint: "\u5efa\u8b70\u4e0a\u50b3\u9910\u76e4\u5167\u5bb9\u6e05\u695a\u3001\u4e3b\u98df\u660e\u986f\u7684\u7167\u7247",
  selectedFile: "\u5df2\u9078\u64c7\u6a94\u6848\uff1a",
  previewAlt: "\u9910\u9ede\u9810\u89bd",
  previewPlaceholder: "\u5716\u7247\u9810\u89bd\u6703\u986f\u793a\u5728\u9019\u88e1",
  analyzing: "\u5206\u6790\u4e2d...",
  submit: "\u958b\u59cb\u5206\u6790",
};

function UploadPanel({
  previewUrl,
  selectedFile,
  error,
  loading,
  onFileChange,
  onSubmit,
  foodProfiles,
  foodProfilesLoading,
  foodProfilesError,
  onManualLookupChange,
  appliedManualLookup,
  onApplyManualLookup,
  onClearAppliedManualLookup,
}) {
  const [isDragging, setIsDragging] = useState(false);

  function handleDragEnter(event) {
    event.preventDefault();
    setIsDragging(true);
  }

  function handleDragOver(event) {
    event.preventDefault();
    setIsDragging(true);
  }

  function handleDragLeave(event) {
    event.preventDefault();
    if (event.currentTarget === event.target) {
      setIsDragging(false);
    }
  }

  function handleDrop(event) {
    event.preventDefault();
    setIsDragging(false);
    const file = event.dataTransfer.files?.[0];
    if (!file) {
      return;
    }
    onFileChange({ target: { files: [file] } });
  }

  return (
    <section className="panel-card">
      <div className="section-heading">
        <p className="eyebrow">{COPY.analysis}</p>
        <h2>{COPY.title}</h2>
      </div>

      <label
        className={`upload-dropzone ${isDragging ? "is-dragging" : ""}`}
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          type="file"
          accept=".jpg,.jpeg,.png,image/png,image/jpeg"
          onChange={onFileChange}
        />
        <span>{COPY.chooseImage}</span>
        <small>{COPY.uploadHint}</small>
      </label>

      {selectedFile ? (
        <div className="selected-file">
          {COPY.selectedFile}
          {selectedFile.name}
        </div>
      ) : null}

      {previewUrl ? (
        <div className="preview-wrapper meal-preview scanner-preview">
          <img src={previewUrl} alt={COPY.previewAlt} className="preview-image" />
        </div>
      ) : (
        <div className="preview-placeholder">{COPY.previewPlaceholder}</div>
      )}

      {error ? <div className="error-banner">{error}</div> : null}

      <button className="primary-button full-width" onClick={onSubmit} disabled={loading}>
        {loading ? COPY.analyzing : COPY.submit}
      </button>

      <ManualNutritionLookup
        profiles={foodProfiles}
        loading={foodProfilesLoading}
        error={foodProfilesError}
        onSelectionChange={onManualLookupChange}
        appliedSelection={appliedManualLookup}
        onApplySelection={onApplyManualLookup}
        onClearAppliedSelection={onClearAppliedManualLookup}
      />
    </section>
  );
}

export default UploadPanel;

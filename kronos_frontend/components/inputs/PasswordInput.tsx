import React, { useEffect, useState } from "react";
import { FieldErrors, FieldValues, UseFormRegister } from "react-hook-form";
import { IoEyeOffOutline, IoEyeOutline } from "react-icons/io5";

interface PassWordInputProps {
  id: string;
  label: string;
  disabled?: boolean;
  required?: boolean;
  placeholder?: string;
  register: UseFormRegister<FieldValues>;
  errors: FieldErrors;
  className?: string;
  autoComplete?: string;
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

const PassWordInput: React.FC<PassWordInputProps> = ({
  id, label, disabled = false, required = false, placeholder = "",
  register, errors, className = "", autoComplete = "off", value, onChange = () => {},
}) => {
  const [hasValue, setHasValue] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const hasError = !!errors[id];

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setHasValue(!!e.target.value);
  };

  useEffect(() => {
    if (!disabled) setHasValue(false);
  }, [disabled]);

  return (
    <div className="flex flex-col items-start w-full">
      <div className="relative w-full">
        {/* Floating label */}
        <label
          htmlFor={id}
          className="absolute z-10 pointer-events-none"
          style={{
            fontSize: hasValue || hasError ? "11px" : "14px",
            fontWeight: 500,
            top: hasValue || hasError ? "9px" : "20px",
            left: "14px",
            color: hasError ? "var(--tv-down)" : hasValue ? "var(--tv-accent)" : "var(--tv-text-3)",
            transition:
              "top var(--tv-dur-fast) var(--tv-ease), font-size var(--tv-dur-fast) var(--tv-ease), color var(--tv-dur-fast) var(--tv-ease)",
          }}
        >
          {label}
        </label>

        {/* Input */}
        <input
          type={showPassword ? "text" : "password"}
          id={id}
          className={`w-full h-[60px] px-3.5 pt-5 outline-none ${className}`}
          style={{
            borderRadius: "var(--tv-radius)",
            background: "var(--tv-surface)",
            boxShadow: "var(--tv-shadow-1)",
            color: "var(--tv-text-1)",
            border: hasError
              ? "1px solid var(--tv-down)"
              : "1px solid var(--tv-border-strong)",
            fontSize: "15px",
            transition:
              "border-color var(--tv-dur-fast) var(--tv-ease), box-shadow var(--tv-dur-fast) var(--tv-ease)",
          }}
          placeholder={placeholder}
          disabled={disabled}
          {...register(id, { required })}
          autoComplete={autoComplete}
          value={value}
          onInput={(e: React.FormEvent<HTMLInputElement>) => {
            onChange(e as React.ChangeEvent<HTMLInputElement>);
            handleInputChange(e as React.ChangeEvent<HTMLInputElement>);
          }}
          onFocus={(e) => {
            e.target.style.borderColor = "var(--tv-accent)";
            e.target.style.boxShadow = "0 0 0 3px var(--tv-accent-soft)";
          }}
          onBlur={(e) => {
            e.target.style.borderColor = hasError
              ? "var(--tv-down)"
              : "var(--tv-border-strong)";
            e.target.style.boxShadow = "var(--tv-shadow-1)";
          }}
        />

        {/* Eye toggle */}
        <button
          type="button"
          className="absolute right-4 top-1/2 -translate-y-1/2"
          style={{ color: "var(--tv-text-3)", background: "none", border: "none", cursor: "pointer" }}
          onClick={() => setShowPassword((p) => !p)}
        >
          {showPassword ? <IoEyeOutline size={20} /> : <IoEyeOffOutline size={20} />}
        </button>
      </div>

      {hasError && (
        <span
          className="mt-1.5 ml-1"
          style={{ fontSize: "12px", color: "var(--tv-down)" }}
        >
          {label} is required
        </span>
      )}
    </div>
  );
};

export default PassWordInput;

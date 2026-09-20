import React, { useEffect, useState } from "react";
import { FieldErrors, FieldValues, UseFormRegister } from "react-hook-form";
import { IconType } from "react-icons";
import { MdMailOutline } from "react-icons/md";

interface InputProps {
  id: string;
  label: string;
  type?: string;
  disabled?: boolean;
  required?: boolean;
  placeholder?: string;
  maxLength?: number;
  register: UseFormRegister<FieldValues>;
  errors: FieldErrors;
  icon?: IconType;
  className?: string;
  autoComplete?: string;
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

// 2026-08 ground-up rework: token-driven floating-label field (works in both
// themes), sentence-case label, accent focus ring, calm error state.
const Input: React.FC<InputProps> = ({
  id, label, type = "text", disabled = false, required = false,
  placeholder = "", register, maxLength, errors,
  icon: Icon, className = "", autoComplete = "off", value, onChange = () => {},
}) => {
  const [hasValue, setHasValue] = useState(false);
  const hasError = !!errors[id];
  const floated = hasValue || hasError;

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
            fontSize: floated ? "11px" : "14px",
            fontWeight: 500,
            top: floated ? "9px" : "20px",
            left: "14px",
            color: hasError
              ? "var(--tv-down)"
              : floated
                ? "var(--tv-accent)"
                : "var(--tv-text-3)",
            transition:
              "top var(--tv-dur-fast) var(--tv-ease), font-size var(--tv-dur-fast) var(--tv-ease), color var(--tv-dur-fast) var(--tv-ease)",
          }}
        >
          {label}
        </label>

        {/* Input */}
        <input
          type={type}
          id={id}
          className={`w-full h-[60px] px-3.5 pt-5 outline-none ${className}`}
          style={{
            borderRadius: "var(--tv-radius)",
            background: "var(--tv-surface)",
            border: hasError
              ? "1px solid var(--tv-down)"
              : "1px solid var(--tv-border-strong)",
            boxShadow: "var(--tv-shadow-1)",
            color: "var(--tv-text-1)",
            fontSize: "15px",
            transition:
              "border-color var(--tv-dur-fast) var(--tv-ease), box-shadow var(--tv-dur-fast) var(--tv-ease)",
          }}
          placeholder={placeholder}
          disabled={disabled}
          {...register(id, { required })}
          autoComplete={autoComplete}
          value={value}
          maxLength={maxLength}
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

        {/* Icon */}
        <span
          className="absolute right-3.5 top-1/2 -translate-y-1/2"
          style={{ color: "var(--tv-text-3)" }}
        >
          {Icon ? <Icon size={18} /> : <MdMailOutline size={18} />}
        </span>
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

export default Input;

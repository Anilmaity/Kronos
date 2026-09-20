"use client";
import { client } from "@/GraphQL/client";
import Logo from "@/components/logo";
import { Button } from "@/components/ui/button";
import { apiUrl } from "@/constants";
import { useUserToken } from "@/hooks/useUserToken";
import { gql } from "@apollo/client";
import axios from "axios";
import { useRouter } from "next/navigation";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { useAuthStep } from "@/hooks/useAuthStep";
import { ArrowLeftIcon } from "lucide-react";
import { STORAGE_KEYS } from "@/lib/storage";

const OTPForm = () => {
  const [isLoading, setIsLoading] = React.useState(false); // for handling loading state of the form

  const { setStep } = useAuthStep();

  const router = useRouter();

  const length = 6;

  const otpValidityTime = 60;

  const [otp, setOtp] = useState(new Array(length).fill(""));

  const [timer, setTimer] = useState(otpValidityTime);

  const [focusedIndex, setFocusedIndex] = useState<number | null>(null);

  const [otpSent, setOtpSent] = useState<boolean>(
    localStorage.getItem(STORAGE_KEYS.otpSent) === "True"
  );

  const inputRefs = useRef<Array<HTMLInputElement | null>>([]); // Ref to store the input fields

  const { setUserToken } = useUserToken(); // Custom hook to get the user token

  const saveTimeStamp = useCallback(() => {
    setOtpSent(true);
    localStorage.setItem(STORAGE_KEYS.otpSent, "True");
    const currentTime = Math.floor(Date.now() / 1000);
    localStorage.setItem(STORAGE_KEYS.otpTimestamp, currentTime.toString());
  }, []); // Save the current time to the local storage and clear the local storage

  useEffect(() => {
    if (timer === 0) {
      if (localStorage.getItem(STORAGE_KEYS.otpSent) === "True") {
        setOtpSent(false);
        localStorage.setItem(STORAGE_KEYS.otpSent, "False");
      }
    } else {
      const timerId = setInterval(() => {
        setTimer((prevTimer) => prevTimer - 1);
      }, 1000);
      return () => {
        clearInterval(timerId);
      };
    }
  }, [timer, otpSent]); // Set the timer to decrement by 1 every second and clear the interval when the component is unmounted

  useEffect(() => {
    const savedTimeStamp = localStorage.getItem(STORAGE_KEYS.otpTimestamp);
    if (savedTimeStamp) {
      const currentTime = Math.floor(Date.now() / 1000);
      const timeDifference = currentTime - parseInt(savedTimeStamp);
      if (timeDifference < otpValidityTime) {
        setTimer(otpValidityTime - timeDifference);
      } else if (timeDifference >= otpValidityTime) {
        setOtpSent(false);
        localStorage.setItem(STORAGE_KEYS.otpSent, "False");
        setTimer(0);
      }
    } else {
      saveTimeStamp();
    }
  }, [saveTimeStamp]);

  const onSubmit = (e: React.MouseEvent<HTMLButtonElement, MouseEvent>) => {
    e?.preventDefault(); // Prevent the default behaviour of the form
    if (otpSent) {
      // Logic to validate OTP
      const newOtp = [...otp]; // Copy the OTP
      const combinedOtp = newOtp.join(""); // Combine the OTP
      if (
        combinedOtp.length === length &&
        !/\s/.test(newOtp[length - 1]) &&
        !/\s/.test(newOtp[length - 2]) &&
        !/\s/.test(newOtp[length - 3]) &&
        !/\s/.test(newOtp[length - 4]) &&
        !/\s/.test(newOtp[length - 5]) &&
        !/\s/.test(newOtp[length - 6])
      ) {
        setIsLoading(true); // Set the loading state to true
        const userEmail = localStorage.getItem(STORAGE_KEYS.userEmail); // Get the user email from the local storage
        const password = localStorage.getItem(STORAGE_KEYS.password); // Get the password from the local storage
        axios
          .post(
            `${apiUrl}/validate-otp/`,
            {
              email: userEmail,
              otp: combinedOtp,
              password: password,
            },
            {
              headers: {
                "Content-Type": "application/json",
              },
            }
          ) // Send a POST request to the server to validate the OTP
          .then((res) => {
            if (res.data.success) {
              setTimer(0); // Set the timer to 0
              setOtpSent(false); // Set otpSent to false
              localStorage.clear();
              setUserToken(res.data.data.Login.token);
              localStorage.setItem(STORAGE_KEYS.token, res.data.data.Login.token);
              localStorage.setItem(
                STORAGE_KEYS.userEmail,
                res.data.data.Login.User.email
              );
              localStorage.setItem(
                STORAGE_KEYS.isSuperuser,
                res.data.data.Login.User.isSuperuser
              );
              toast.success("OTP Validated Sucessfully");
              router.push("/dashboard");
            }
          }) // If the OTP is validated successfully then set the timer to 0, set otpSent to false, clear the local storage, save the token, user email and isSuperuser to the local storage, show a success message and redirect the user to the dashboard
          .catch((error) => {
            toast.error(error.response.data.data.message);
          }) // If there is an error then show an error message
          .finally(() => {
            setIsLoading(false);
          }); // Set the loading state to false
      }
    } else {
      setIsLoading(true);
      // Logic to resend OTP
      e.preventDefault();
      setOtp(new Array(length).fill("")); // Clear OTP fields
      const email = localStorage.getItem(STORAGE_KEYS.userEmail);
      const password = localStorage.getItem(STORAGE_KEYS.password);

      // mutation to resend the OTP
      const mutation = gql`
      mutation {
      Login(email: "${email}", password: "${password}"){
          Response
        }
      }
    `;
      client
        .mutate({
          mutation: mutation,
          fetchPolicy: "no-cache",
        })
        .then((res) => {
          if (res.data.Login.Response.includes("Success")) {
            toast.success("An OTP has been sent to your email address.");
            saveTimeStamp();
            setTimer(otpValidityTime);
          } else {
            toast.error(res.data.Login.Response);
          }
        }) // If the response contains the word success then get the otp and show a success message, save the time stamp and set the timer to the OTP validity time
        .catch((err) => {
          toast.error(err.message);
        }) // If there is an error then show the error message
        .finally(() => {
          setIsLoading(false);
        }); // Set the loading state to false
    }
  }; // If the OTP has been sent then validate the OTP and if the OTP has not been sent then resend the OTP

  const handleChange = (
    index: number,
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const value = e.target.value; // Get the value of the input field
    if (isNaN(Number(value))) return; // Check if the value is a number or not
    const numericValue = value.replace(/\D/g, ""); // Remove all non-numeric characters from the value
    const newOtp = [...otp]; // Copy the OTP
    newOtp[index] = numericValue.substring(numericValue.length - 1); // Set the value of the input field to the last character of the numeric value
    setOtp(newOtp); // Set the OTP to the new OTP
    if (numericValue && index < length - 1 && inputRefs.current[index + 1]) {
      inputRefs.current[index + 1]?.focus();
    } // If the numeric value is not empty and the index is less than the length of the OTP minus 1 and the next input field is available then focus on the next input field
  }; // Remove all non-numeric characters from the value and set the value of the input field to the last character of the numeric value

  const handleClick = (index: number) => {
    inputRefs.current[index]?.setSelectionRange(1, 1); // Set the selection range of the input field to 1, 1
    if (index > 0 && !otp[index - 1]) {
      inputRefs.current[otp.indexOf("")]?.focus();
    } // If the index is greater than 0 and the previous input field is empty then focus on the first empty input field
  }; // Set the selection range of the input field to 1, 1 and if the previous input field is empty then focus on the first empty input field

  const handleKeyDown = (
    index: number,
    e: React.KeyboardEvent<HTMLInputElement>
  ) => {
    if (e.key === "Backspace" && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
      setTimeout(() => {
        inputRefs.current[index - 1]?.setSelectionRange(1, 1);
      });
    } // If the key is backspace and the input field is empty and the index is greater than 0 then focus on the previous input field and set the selection range of the input field to 1, 1
    if (e.key === "ArrowLeft" && index > 0) {
      inputRefs.current[index - 1]?.focus();
      setTimeout(() => {
        inputRefs.current[index - 1]?.setSelectionRange(1, 1);
      });
    } // If the key is arrow left and the index is greater than 0 then focus on the previous input field and set the selection range of the input field to 1, 1
  }; // If the key is backspace and the input field is empty and the index is greater than 0 then focus on the previous input field and set the selection range of the input field to 1, 1 and if the key is arrow left and the index is greater than 0 then focus on the previous input field and set the selection range of the input field to 1, 1

  useEffect(() => {
    if (inputRefs.current[0]) {
      inputRefs.current[0].focus();
    } // If the input field is available then focus on the input field
  }, []); // If the input field is available then focus on the input field

  return (
    <div className="flex flex-col items-center gap-5">
      {/* Back button */}
      <div className="w-full">
        <Button
          variant="outline"
          onClick={() => {
            localStorage.clear();
            setStep("LOGIN");
          }}
          className="flex items-center gap-1"
          style={{ borderRadius: 6 }}
        >
          <ArrowLeftIcon className="w-4 h-4" />
          <span>Back</span>
        </Button>
      </div>

      <Logo />

      <div className="flex flex-col items-center gap-2 text-center">
        <div
          style={{
            fontSize: "20px",
            fontWeight: 600,
            color: "var(--tv-text-1)",
          }}
        >
          Enter OTP
        </div>
        <div
          style={{
            fontSize: "13px",
            color: "var(--tv-text-3)",
          }}
        >
          Please enter the OTP sent to your email address
        </div>
      </div>

      <div className="w-full">
        <form className="flex flex-col items-center w-full gap-4">
          <div className="flex items-center gap-2 justify-center">
            {otp.map((value, index) => (
              <input
                ref={(input) => (inputRefs.current[index] = input)}
                key={`otp_${index + 1}`}
                type="text"
                style={{
                  textAlign: "center",
                  border: focusedIndex === index
                    ? "2px solid var(--tv-accent)"
                    : "1px solid var(--tv-border)",
                  borderRadius: 6,
                  width: 44,
                  height: 52,
                  fontSize: 18,
                  fontWeight: 600,
                  background: "transparent",
                  color: "var(--tv-text-1)",
                  outline: "none",
                  transition: "border-color 0.15s",
                }}
                value={otp[index]}
                onChange={(e) => {
                  handleChange(index, e);
                }}
                onClick={() => handleClick(index)}
                onKeyDown={(e) => {
                  handleKeyDown(index, e);
                }}
                onFocus={() => setFocusedIndex(index)}
                onBlur={() => setFocusedIndex(null)}
                disabled={isLoading || !otpSent}
              />
            ))}
          </div>
          <Button
            onClick={onSubmit}
            className="w-full"
            disabled={isLoading}
          >
            {otpSent ? "Submit" : "Resend OTP"}
          </Button>
          {timer > 0 && (
            <div
              style={{
                fontSize: "13px",
                fontWeight: 500,
                color: timer <= 5 ? "var(--tv-down)" : "var(--tv-text-2)",
              }}
            >
              Time left: {timer} seconds
            </div>
          )}
        </form>
      </div>
    </div>
  );
};

export default OTPForm;

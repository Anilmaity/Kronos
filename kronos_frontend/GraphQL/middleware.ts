import { toast } from "sonner";

// Messages the backend emits when the JWT is missing, invalid, or expired.
const AUTH_ERROR_MESSAGES = [
  "Signature has expired",
  "Authentication Failure : You must be signed in",
];

// Apollo joins every GraphQL error message with "\n" into err.message, so a
// multi-root-field query (e.g. StrategyManagerState) that fails auth produces
// the auth message repeated N times — never strictly equal to a single one.
// Check each underlying error (and the joined message) by inclusion instead.
function isAuthFailure(err: any): boolean {
  const messages: string[] = [
    ...(err?.graphQLErrors ?? []).map((e: any) => e?.message ?? ""),
    err?.message ?? "",
  ];
  return messages.some((msg) =>
    AUTH_ERROR_MESSAGES.some((auth) => msg.includes(auth))
  );
}

function middleware(err: any) {
  if (isAuthFailure(err)) {
    localStorage.clear();
    window.location.href = "/login";
  } else {
    toast.error(err.message);
  }
}

export { middleware, isAuthFailure };

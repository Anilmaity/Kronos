"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { client } from "@/GraphQL/client";
import { middleware } from "@/GraphQL/middleware";
import { Button } from "@/components/ui/button";
import {
  ADD_ACCOUNT,
  UPDATE_ACCOUNT,
  DELETE_USER_BROKER,
  GET_ACCOUNTS,
} from "@/GraphQL/accountControls";
import { panelStyle, soft, fieldStyle } from "@/lib/tvStyles";

interface Account {
  id: string;
  label: string;
  metaAccountId: string;
  metaApiTokenLast4: string;
  hasToken: boolean;
  isActive: boolean;
  status: string;
}

const emptyForm = { id: "", label: "", metaAccountId: "", metaApiToken: "" };

const AccountsManager: React.FC = () => {
  const router = useRouter();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [form, setForm] = useState({ ...emptyForm });
  const [editing, setEditing] = useState(false);

  const load = () => {
    client
      .query({ query: GET_ACCOUNTS, fetchPolicy: "no-cache" })
      .then((res) => {
        setAccounts(res.data?.getuserdata?.userbrokers ?? []);
      })
      .catch((err) => middleware(err));
  };

  useEffect(() => {
    load();
  }, []);

  const resetForm = () => {
    setForm({ ...emptyForm });
    setEditing(false);
  };

  const handleSubmit = () => {
    if (editing) {
      const variables: Record<string, string> = {
        id: form.id,
        label: form.label,
        metaAccountId: form.metaAccountId,
      };
      if (form.metaApiToken) variables.metaApiToken = form.metaApiToken;
      client
        .mutate({ mutation: UPDATE_ACCOUNT, variables, fetchPolicy: "no-cache" })
        .then((res) => {
          if (res.data.UpdateAccount.Response === "Success") {
            toast.success("Account updated");
            resetForm();
            load();
          } else {
            toast.error(res.data.UpdateAccount.Response);
          }
        })
        .catch((err) => middleware(err));
    } else {
      client
        .mutate({
          mutation: ADD_ACCOUNT,
          variables: {
            label: form.label,
            metaAccountId: form.metaAccountId,
            metaApiToken: form.metaApiToken,
          },
          fetchPolicy: "no-cache",
        })
        .then((res) => {
          if (res.data.AddAccount.Response === "Success") {
            toast.success("Account added");
            resetForm();
            load();
          } else {
            toast.error(res.data.AddAccount.Response);
          }
        })
        .catch((err) => middleware(err));
    }
  };

  const handleEdit = (a: Account) => {
    setForm({
      id: a.id,
      label: a.label,
      metaAccountId: a.metaAccountId,
      metaApiToken: "",
    });
    setEditing(true);
  };

  const handleDelete = (id: string) => {
    if (
      typeof window !== "undefined" &&
      !window.confirm("Delete this account? This cannot be undone.")
    ) {
      return;
    }
    client
      .mutate({
        mutation: DELETE_USER_BROKER,
        variables: { brokerId: id },
        fetchPolicy: "no-cache",
      })
      .then((res) => {
        if (res.data.DeleteUserBroker.Response === "Success") {
          toast.success("Account deleted");
          load();
        } else {
          toast.error(res.data.DeleteUserBroker.Response);
        }
      })
      .catch((err) => middleware(err));
  };

  return (
    <div className="flex flex-col items-start w-full gap-6">
      <div className="flex flex-col">
        <span className="text-base font-semibold">Accounts</span>
        <span className="text-sm" style={soft}>
          MetaAPI broker accounts
        </span>
      </div>

      <div className="flex flex-col gap-3 p-4 max-w-xl w-full" style={panelStyle}>
        <div className="font-semibold">
          {editing ? "Edit account" : "Add account"}
        </div>
        <input
          style={fieldStyle}
          placeholder="Label (e.g. Primary Live)"
          value={form.label}
          onChange={(e) => setForm({ ...form, label: e.target.value })}
        />
        <input
          style={fieldStyle}
          placeholder="MetaAPI account ID"
          value={form.metaAccountId}
          onChange={(e) => setForm({ ...form, metaAccountId: e.target.value })}
        />
        <input
          style={fieldStyle}
          type="password"
          placeholder={
            editing ? "Token (leave blank to keep current)" : "MetaAPI token"
          }
          value={form.metaApiToken}
          onChange={(e) => setForm({ ...form, metaApiToken: e.target.value })}
        />
        <div className="flex gap-2">
          <Button size="sm" onClick={handleSubmit}>
            {editing ? "Save" : "Add"}
          </Button>
          {editing && (
            <Button size="sm" variant="ghost" onClick={resetForm}>
              Cancel
            </Button>
          )}
        </div>
      </div>

      <div className="flex flex-col gap-2 w-full">
        {accounts.length === 0 && (
          <div className="text-sm" style={soft}>
            No accounts yet.
          </div>
        )}
        {accounts.map((a) => (
          <div
            key={a.id}
            className="flex items-center justify-between px-4 py-3 w-full"
            style={panelStyle}
          >
            <div className="flex flex-col">
              <span className="font-semibold">{a.label || "(no label)"}</span>
              <span className="text-sm" style={soft}>
                {a.metaAccountId}
              </span>
            </div>
            <div className="text-sm" style={soft}>
              {a.hasToken ? `••••${a.metaApiTokenLast4}` : "no token set"}
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                className="tv-chip"
                onClick={() => router.push(`/accounts/${a.id}`)}
              >
                View analytics
              </button>
              <button
                type="button"
                className="tv-chip"
                onClick={() => handleEdit(a)}
              >
                Edit
              </button>
              <button
                type="button"
                className="tv-chip tv-chip--danger"
                onClick={() => handleDelete(a.id)}
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AccountsManager;

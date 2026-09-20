// React - Next default
"use client";
import React, { useEffect, useState } from "react";

interface ClientOnlyProps {
  children: React.ReactNode;
}

const ClientOnly: React.FC<ClientOnlyProps> = ({ children }) => {
  const [hasMounted, setHasMounted] = useState(false);

  useEffect(() => {
    setHasMounted(true);
  }, []); // useEffect is a hook that runs a function when a component is mounted or updated

  if (!hasMounted) {
    return null;
  } // if the component has not mounted, return null

  return children;
};

export default ClientOnly;

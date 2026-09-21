"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/users", label: "Users" },
  { href: "/households", label: "Households" },
  { href: "/reports", label: "Reports" },
  { href: "/analytics", label: "Analytics" },
  { href: "/approvals", label: "Approvals" },
  { href: "/audit", label: "Audit" },
  { href: "/security", label: "Security" },
];

export function AdminNav() {
  const pathname = usePathname();

  return (
    <div className="nav">
      {NAV_ITEMS.map((item) => {
        const active = pathname === item.href;
        return (
          <Link key={item.href} href={item.href} aria-current={active ? "page" : undefined} className={active ? "nav-link active" : "nav-link"}>
            {item.label}
          </Link>
        );
      })}
    </div>
  );
}

import SignUpForm from "@/components/auth/SignUpForm";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "feraSet Kayit",
  description: "feraSet sirket hesabi olusturun.",
};

export default function SignUp() {
  return <SignUpForm />;
}

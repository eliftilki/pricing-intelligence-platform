import SignUpForm from "@/components/auth/SignUpForm";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "feraSet Kayıt",
  description: "feraSet şirket hesabı oluşturun.",
};

export default function SignUp() {
  return <SignUpForm />;
}

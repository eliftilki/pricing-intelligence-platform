import SignInForm from "@/components/auth/SignInForm";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "feraSet Giriş",
  description: "feraSet şirket paneline giriş yapın.",
};

export default function SignIn() {
  return <SignInForm />;
}

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RiskGauge } from "../components/RiskGauge";

describe("RiskGauge", () => {
  it("renders the risk number and tier", () => {
    render(<RiskGauge risk={82} tier="CRITICAL" />);
    expect(screen.getByText("82")).toBeInTheDocument();
    expect(screen.getByText("CRITICAL")).toBeInTheDocument();
  });
});

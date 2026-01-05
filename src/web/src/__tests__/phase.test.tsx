import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatBlock } from "../components/StatBlock/StatBlock";
import type { GamePhase, LocalizedString } from "../api/types";

describe("StatBlock Phase Display", () => {
  const defaultProps = {
    playerName: "测试玩家",
    characterName: "测试角色",
    concept: { cn: "勇敢的探险者", en: "Brave Explorer" } as LocalizedString,
    location: "书房",
    turnCount: 1,
    fatePoints: 3,
    traits: [],
    tags: ["新手"],
    language: "cn" as const,
  };

  describe("Phase labels in Chinese", () => {
    it("displays '等待输入' for waiting_input phase", () => {
      render(<StatBlock {...defaultProps} phase="waiting_input" />);
      expect(screen.getByText("等待输入")).toBeInTheDocument();
    });

    it("displays '处理行动' for processing phase", () => {
      render(<StatBlock {...defaultProps} phase="processing" />);
      expect(screen.getByText("处理行动")).toBeInTheDocument();
    });

    it("displays '骰子检定' for dice_check phase", () => {
      render(<StatBlock {...defaultProps} phase="dice_check" />);
      expect(screen.getByText("骰子检定")).toBeInTheDocument();
    });

    it("displays 'NPC 回应' for npc_response phase", () => {
      render(<StatBlock {...defaultProps} phase="npc_response" />);
      expect(screen.getByText("NPC 回应")).toBeInTheDocument();
    });

    it("displays '叙述中' for narrating phase", () => {
      render(<StatBlock {...defaultProps} phase="narrating" />);
      expect(screen.getByText("叙述中")).toBeInTheDocument();
    });
  });

  describe("Phase labels in English", () => {
    const englishProps = { ...defaultProps, language: "en" as const };

    it("displays 'Waiting Input' for waiting_input phase", () => {
      render(<StatBlock {...englishProps} phase="waiting_input" />);
      expect(screen.getByText("Waiting Input")).toBeInTheDocument();
    });

    it("displays 'Processing' for processing phase", () => {
      render(<StatBlock {...englishProps} phase="processing" />);
      expect(screen.getByText("Processing")).toBeInTheDocument();
    });

    it("displays 'Dice Check' for dice_check phase", () => {
      render(<StatBlock {...englishProps} phase="dice_check" />);
      expect(screen.getByText("Dice Check")).toBeInTheDocument();
    });

    it("displays 'NPC Response' for npc_response phase", () => {
      render(<StatBlock {...englishProps} phase="npc_response" />);
      expect(screen.getByText("NPC Response")).toBeInTheDocument();
    });

    it("displays 'Narrating' for narrating phase", () => {
      render(<StatBlock {...englishProps} phase="narrating" />);
      expect(screen.getByText("Narrating")).toBeInTheDocument();
    });
  });

  describe("Phase indicator styling", () => {
    it("renders phase indicator with amber styling", () => {
      render(<StatBlock {...defaultProps} phase="waiting_input" />);
      const phaseElement = screen.getByText("等待输入").closest("p");
      expect(phaseElement).toHaveClass("bg-amber-50");
      expect(phaseElement).toHaveClass("text-amber-800");
    });

    it("renders phase status indicator dot", () => {
      render(<StatBlock {...defaultProps} phase="processing" />);
      const phaseElement = screen.getByText("处理行动").closest("p");
      const dot = phaseElement?.querySelector('[aria-hidden="true"]');
      expect(dot).toBeInTheDocument();
      expect(dot).toHaveClass("bg-amber-400");
    });
  });
});

describe("GamePhase type coverage", () => {
  const allPhases: GamePhase[] = [
    "waiting_input",
    "processing",
    "dice_check",
    "npc_response",
    "narrating",
  ];

  it("covers all expected phases", () => {
    expect(allPhases).toHaveLength(5);
  });

  it("all phases are valid string literals", () => {
    allPhases.forEach((phase) => {
      expect(typeof phase).toBe("string");
      expect(phase.length).toBeGreaterThan(0);
    });
  });
});

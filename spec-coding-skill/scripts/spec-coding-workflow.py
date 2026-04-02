#!/usr/bin/env python3
"""
Spec Coding Multi-Agent Workflow Orchestrator
Triggers and coordinates 7 agents to complete a software project
"""

import argparse
import json
import os
import sys
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import subprocess


class WorkflowContext:
    """Manages the shared architecture context across all agents"""
    
    def __init__(self, project_path: str, project_name: str):
        self.project_path = Path(project_path)
        self.project_name = project_name
        self.context_file = self.project_path / "context" / "state.yaml"
        self.load()
    
    def load(self):
        """Load existing context or initialize new"""
        if self.context_file.exists():
            with open(self.context_file) as f:
                self.state = yaml.safe_load(f)
        else:
            self.state = self._init_state()
    
    def _init_state(self) -> dict:
        """Initialize empty context state"""
        return {
            "project": {
                "name": self.project_name,
                "created_at": datetime.now().isoformat(),
                "status": "initialized",
                "current_phase": None
            },
            "phases": {},
            "master_framework": None,
            "global_state": {
                "modules": {},
                "dependencies": [],
                "active_agents": 0
            },
            "event_bus": {
                "subscriptions": [],
                "history": []
            }
        }
    
    def save(self):
        """Persist context to disk"""
        self.context_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.context_file, 'w') as f:
            yaml.dump(self.state, f, default_flow_style=False)
    
    def update_phase(self, phase_name: str, status: str, output: dict = None):
        """Update phase status in context"""
        self.state["phases"][phase_name] = {
            "status": status,
            "updated_at": datetime.now().isoformat(),
            "output": output or {}
        }
        self.state["project"]["current_phase"] = phase_name
        self.save()
    
    def set_master_framework(self, framework: dict):
        """Set master framework (created by Agent 2)"""
        self.state["master_framework"] = framework
        self.save()
    
    def publish_event(self, event_type: str, payload: dict, source_agent: str):
        """Publish event to event bus"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "source": source_agent,
            "payload": payload
        }
        self.state["event_bus"]["history"].append(event)
        self.save()
        return event


class AgentRunner:
    """Runs individual agents as sub-processes"""
    
    def __init__(self, context: WorkflowContext, skill_path: Path):
        self.context = context
        self.skill_path = skill_path
        self.prompts_path = skill_path / "resources" / "prompts"
    
    def run_agent(self, agent_name: str, input_data: dict, 
                  wait_for_human: bool = False) -> dict:
        """
        Run an agent and return its output
        
        In real implementation, this would:
        1. Load the agent's prompt template
        2. Call the LLM API
        3. Parse the output
        4. Update the context
        
        For now, we simulate with subprocess call
        """
        print(f"\n{'='*60}")
        print(f"Running {agent_name}...")
        print(f"{'='*60}\n")
        
        # Prepare agent input
        agent_input = {
            "agent_name": agent_name,
            "context": self.context.state,
            "input": input_data,
            "human_checkpoint": wait_for_human
        }
        
        # Call agent script
        agent_script = self.skill_path / "scripts" / f"agent-{agent_name}.py"
        
        if agent_script.exists():
            result = subprocess.run(
                [sys.executable, str(agent_script)],
                input=json.dumps(agent_input),
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                output = json.loads(result.stdout)
                return output
            else:
                raise RuntimeError(f"Agent {agent_name} failed: {result.stderr}")
        else:
            # Simulate agent execution
            return self._simulate_agent(agent_name, input_data)
    
    def _simulate_agent(self, agent_name: str, input_data: dict) -> dict:
        """Simulate agent execution for demo"""
        print(f"[SIMULATION] {agent_name} would execute here")
        print(f"[SIMULATION] Input: {json.dumps(input_data, indent=2)[:500]}...")
        
        # Return simulated output
        return {
            "status": "success",
            "artifacts": {},
            "next_phase": None
        }


class SpecCodingWorkflow:
    """Main workflow orchestrator"""
    
    def __init__(self, project_name: str, project_path: str, 
                 skill_path: str = None):
        self.project_name = project_name
        self.project_path = Path(project_path)
        self.skill_path = Path(skill_path or ".")
        
        # Initialize context
        self.context = WorkflowContext(project_path, project_name)
        
        # Initialize agent runner
        self.agent_runner = AgentRunner(self.context, self.skill_path)
        
        # Define workflow phases
        self.phases = [
            {
                "name": "clarify",
                "agent": "agent-1-clarify",
                "description": "Requirement Clarification",
                "wait_for_human": True,
                "output_dir": "context/requirements"
            },
            {
                "name": "framework",
                "agent": "agent-2-framework",
                "description": "Framework Design",
                "wait_for_human": True,
                "output_dir": "context/framework"
            },
            {
                "name": "decompose",
                "agent": "agent-3-decompose",
                "description": "Task Decomposition",
                "wait_for_human": True,
                "output_dir": "context/tasks"
            },
            {
                "name": "spec",
                "agent": "agent-4-spec",
                "description": "Spec Authoring",
                "wait_for_human": True,
                "output_dir": "specs"
            },
            {
                "name": "harness",
                "agent": "agent-5-harness",
                "description": "Harness Configuration",
                "wait_for_human": True,
                "output_dir": "."
            },
            {
                "name": "coding",
                "agent": "agent-6-coding",
                "description": "Parallel Coding",
                "wait_for_human": False,  # Monitor mode
                "output_dir": "src"
            },
            {
                "name": "certify",
                "agent": "agent-7-certify",
                "description": "Self-Certification",
                "wait_for_human": True,
                "output_dir": "tests"
            }
        ]
    
    def init_project(self, description: str, language: str = "cpp", 
                     **kwargs) -> dict:
        """
        Initialize new project and run complete workflow
        
        Returns project summary
        """
        print(f"\n{'#'*60}")
        print(f"# Spec Coding Multi-Agent Workflow")
        print(f"# Project: {self.project_name}")
        print(f"# Language: {language}")
        print(f"{'#'*60}\n")
        
        # Create project structure
        self._create_project_structure()
        
        # Run all phases
        results = {}
        
        for phase in self.phases:
            print(f"\n{'>'*60}")
            print(f"> Phase: {phase['description']}")
            print(f"> Agent: {phase['agent']}")
            print(f"{'>'*60}")
            
            # Prepare input for agent
            agent_input = self._prepare_agent_input(phase, description, language, kwargs)
            
            # Run agent
            try:
                output = self.agent_runner.run_agent(
                    phase['agent'],
                    agent_input,
                    wait_for_human=phase['wait_for_human']
                )
                
                results[phase['name']] = output
                
                # Update context
                self.context.update_phase(
                    phase['name'],
                    "completed",
                    output.get('artifacts', {})
                )
                
                # Special handling for framework phase
                if phase['name'] == 'framework':
                    self.context.set_master_framework(
                        output.get('framework', {})
                    )
                
                print(f"\n✅ {phase['description']} completed")
                
                # Human checkpoint
                if phase['wait_for_human']:
                    self._human_checkpoint(phase)
                
            except Exception as e:
                print(f"\n❌ {phase['description']} failed: {e}")
                self.context.update_phase(phase['name'], "failed")
                raise
        
        # Generate final summary
        return self._generate_summary(results)
    
    def run_single_phase(self, phase_name: str, **kwargs):
        """Run a single phase (for resuming or regenerating)"""
        phase = next((p for p in self.phases if p['name'] == phase_name), None)
        if not phase:
            raise ValueError(f"Unknown phase: {phase_name}")
        
        print(f"Running single phase: {phase['description']}")
        
        agent_input = self._prepare_agent_input(
            phase, 
            "",  # description not needed for single phase
            "cpp",
            kwargs
        )
        
        output = self.agent_runner.run_agent(
            phase['agent'],
            agent_input,
            wait_for_human=phase['wait_for_human']
        )
        
        self.context.update_phase(
            phase_name,
            "completed",
            output.get('artifacts', {})
        )
        
        return output
    
    def _create_project_structure(self):
        """Create initial project directory structure"""
        dirs = [
            "context/requirements",
            "context/framework",
            "context/tasks",
            "specs/requirements",
            "specs/architecture",
            "specs/interface",
            "src",
            "tests/unit",
            "tests/integration",
            "scripts"
        ]
        
        for d in dirs:
            (self.project_path / d).mkdir(parents=True, exist_ok=True)
        
        print(f"✅ Created project structure at {self.project_path}")
    
    def _prepare_agent_input(self, phase: dict, description: str,
                           language: str, kwargs: dict) -> dict:
        """Prepare input data for an agent"""
        return {
            "phase": phase['name'],
            "project_name": self.project_name,
            "description": description,
            "language": language,
            "project_path": str(self.project_path),
            "output_dir": phase['output_dir'],
            "context_snapshot": self.context.state,
            "options": kwargs
        }
    
    def _human_checkpoint(self, phase: dict):
        """Pause for human review"""
        print(f"\n{'='*60}")
        print(f"⏸️  HUMAN CHECKPOINT: {phase['description']}")
        print(f"{'='*60}")
        print(f"\nPlease review the output in:")
        print(f"  {self.project_path / phase['output_dir']}")
        print(f"\nOptions:")
        print(f"  [A]pprove - Continue to next phase")
        print(f"  [R]eview with feedback - Agent will regenerate")
        print(f"  [E]dit manually - Make changes yourself")
        print(f"  [Q]uit - Save state and exit")
        
        # In real implementation, wait for user input
        # For now, auto-approve in simulation
        print("\n[Auto-approving in 3 seconds...]")
        import time
        time.sleep(3)
        print("✅ Approved")
    
    def _generate_summary(self, results: dict) -> dict:
        """Generate project completion summary"""
        summary = {
            "project": self.project_name,
            "path": str(self.project_path),
            "completed_at": datetime.now().isoformat(),
            "phases_completed": len(results),
            "artifacts": {}
        }
        
        for phase_name, output in results.items():
            summary["artifacts"][phase_name] = list(
                output.get('artifacts', {}).keys()
            )
        
        # Save summary
        summary_file = self.project_path / "PROJECT_SUMMARY.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n{'='*60}")
        print(f"🎉 Project '{self.project_name}' completed!")
        print(f"{'='*60}")
        print(f"\nLocation: {self.project_path}")
        print(f"Summary: {summary_file}")
        print(f"\nPhases completed: {summary['phases_completed']}/7")
        print(f"\nNext steps:")
        print(f"  1. Review generated code in src/")
        print(f"  2. Run tests: cd {self.project_path} && ./run_tests")
        print(f"  3. Check coverage report")
        
        return summary


def main():
    parser = argparse.ArgumentParser(
        description="Spec Coding Multi-Agent Workflow"
    )
    parser.add_argument(
        "command",
        choices=["init", "resume", "regenerate", "context"],
        help="Command to execute"
    )
    parser.add_argument(
        "--project-name", "-n",
        required=True,
        help="Project name"
    )
    parser.add_argument(
        "--description", "-d",
        help="Project description"
    )
    parser.add_argument(
        "--language", "-l",
        default="cpp",
        choices=["cpp", "python", "typescript", "go", "rust"],
        help="Programming language"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output directory"
    )
    parser.add_argument(
        "--phase", "-p",
        help="Specific phase (for resume/regenerate)"
    )
    parser.add_argument(
        "--complexity",
        choices=["simple", "complex"],
        default="simple",
        help="Project complexity"
    )
    
    args = parser.parse_args()
    
    # Determine project path
    project_path = args.output or f"./{args.project_name}"
    
    # Create workflow
    workflow = SpecCodingWorkflow(
        project_name=args.project_name,
        project_path=project_path
    )
    
    # Execute command
    if args.command == "init":
        if not args.description:
            print("Error: --description required for init")
            sys.exit(1)
        
        result = workflow.init_project(
            description=args.description,
            language=args.language,
            complexity=args.complexity
        )
        
        print(json.dumps(result, indent=2))
    
    elif args.command == "resume":
        if not args.phase:
            print("Error: --phase required for resume")
            sys.exit(1)
        workflow.run_single_phase(args.phase)
    
    elif args.command == "regenerate":
        if not args.phase:
            print("Error: --phase required for regenerate")
            sys.exit(1)
        workflow.run_single_phase(args.phase, regenerate=True)
    
    elif args.command == "context":
        print(json.dumps(workflow.context.state, indent=2))


if __name__ == "__main__":
    main()

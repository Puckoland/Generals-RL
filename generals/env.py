import numpy as np
import functools
import pettingzoo
import gymnasium
from copy import copy
from generals.game import Game
from generals.maps import Mapper
from .rendering import Renderer
from collections import OrderedDict


def pz_generals(
    mapper: Mapper = Mapper(),
    agents: list = None,
    reward_fn=None,
    render_mode=None,
):
    """
    Here we apply wrappers to the environment.
    """
    env = PZ_Generals(
        mapper=mapper, agents=agents, reward_fn=reward_fn, render_mode=render_mode
    )
    return env


def gym_generals(
    mapper: Mapper = Mapper(),
    agents: list = None,
    reward_fn=None,
    render_mode=None,
):
    """
    Here we apply wrappers to the environment.
    """
    env = Gym_Generals(
        mapper=mapper, agents=agents, reward_fn=reward_fn, render_mode=render_mode
    )
    return env


class PZ_Generals(pettingzoo.ParallelEnv):
    def __init__(self, mapper=None, agents=None, reward_fn=None, render_mode=None):
        self.render_mode = render_mode
        self.mapper = mapper
        self.possible_agents = [agent.name for agent in agents]

        assert (
            len(self.possible_agents) == len(set(self.possible_agents))
        ), "Agent names must be unique - you can pass custom names to agent constructors."

        self.agent_colors = {agent.name: agent.color for agent in agents}

        self.reward_fn = self.default_rewards if reward_fn is None else reward_fn

    @functools.lru_cache(maxsize=None)
    def observation_space(self, agent_name):
        assert agent_name in self.agents, f"{agent_name} is not a valid agent"
        return self.game.observation_space

    @functools.lru_cache(maxsize=None)
    def action_space(self, agent_name):
        assert agent_name in self.agents, f"{agent_name} is not a valid agent"
        return self.game.action_space

    def render(self, tick_rate=None):
        if self.render_mode == "human":
            self.renderer.render()
            if tick_rate is not None:
                self.renderer.clock.tick(tick_rate)

    def reset(self, seed=None, options={}):
        self.agents = copy(self.possible_agents)

        map = self.mapper.get_map()

        self.game = Game(map, self.possible_agents)

        if self.render_mode == "human":
            from_replay = "from_replay" in options and options["from_replay"] or False
            self.renderer = Renderer(self.game, self.agent_colors, from_replay)

        if "replay_file" in options:
            self.replay = options["replay_file"]
            self.state_history = []
        else:
            self.replay = False

        observations = OrderedDict(
            {agent: self.game._agent_observation(agent) for agent in self.agents}
        )

        infos = {agent: {} for agent in self.agents}
        return observations, infos

    def step(self, action):
        if self.replay:
            self.action_history.append(action)

        observations, infos = self.game.step(action)

        truncated = {agent: False for agent in self.agents}  # no truncation
        terminated = {
            agent: True if self.game.is_done() else False for agent in self.agents
        }
        rewards = self.reward_fn(observations)

        # if any agent dies, all agents are terminated
        terminate = any(terminated.values())
        if terminate:
            self.agents = []
            # if replay is on, store the game
            # if self.replay:
            #     utils.store_replay(self.game.map, self.action_history, self.replay)

        return OrderedDict(observations), rewards, terminated, truncated, infos

    def default_rewards(self, observations):
        """
        Calculate rewards for each agent.
        Give 0 if game still running, otherwise 1 for winner and -1 for loser.
        """
        rewards = {agent: 0 for agent in self.agents}
        game_ended = any(observations[agent]["is_winner"] for agent in self.agents)
        if game_ended:
            for agent in self.agents:
                if observations[agent]["is_winner"]:
                    rewards[agent] = 1
                else:
                    rewards[agent] = -1
        return rewards


class Gym_Generals(gymnasium.Env):
    def __init__(self, mapper=None, agents=None, reward_fn=None, render_mode=None):
        self.render_mode = render_mode
        self.reward_fn = self.default_rewards if reward_fn is None else reward_fn
        self.mapper = mapper

        self.agent_name = agents[0].name
        self.npc = agents[1]

        self.agent_colors = {agent.name: agent.color for agent in agents}

        map = self.mapper.get_map()
        game = Game(map, [self.agent_name, self.npc.name])
        self.observation_space = game.observation_space
        self.action_space = game.action_space

    @functools.lru_cache(maxsize=None)
    def observation_space(self):
        return self.game.observation_space

    @functools.lru_cache(maxsize=None)
    def action_space(self):
        return self.game.action_space

    def render(self, tick_rate=None):
        if self.render_mode == "human":
            self.renderer.render()
            if tick_rate is not None:
                self.renderer.clock.tick(tick_rate)

    def reset(self, map: np.ndarray = None, seed=None, options={}):
        super().reset(seed=seed)
        # If map is not provided, generate a new one
        map = self.mapper.get_map()

        self.game = Game(map, [self.agent_name, self.npc.name])
        self.npc.reset()

        self.observation_space = self.game.observation_space
        self.action_space = self.game.action_space

        if self.render_mode == "human":
            from_replay = "from_replay" in options and options["from_replay"] or False
            self.renderer = Renderer(self.game, self.agent_colors, from_replay)

        if "replay_file" in options:
            self.replay = options["replay_file"]
            self.action_history = []
        else:
            self.replay = False

        observation = OrderedDict(self.game._agent_observation(self.agent_name))
        info = {}
        return observation, info

    def step(self, action):
        # get action of NPC
        npc_action = self.npc.play(self.game._agent_observation(self.npc.name))
        actions = {self.agent_name: action, self.npc.name: npc_action}

        if self.replay:
            self.action_history.append(actions)

        observations, infos = self.game.step(actions)

        observation = observations[self.agent_name]
        info = infos[self.agent_name]
        truncated = False
        terminated = True if self.game.is_done() else False
        reward = self.reward_fn(observations)

        if terminated:
            # if replay is on, store the game
            # if self.replay:
            #     utils.store_replay(self.game.map, self.action_history, self.replay)
            pass

        return OrderedDict(observation), reward, terminated, truncated, info

    def default_rewards(self, observations):
        """
        Calculate rewards for each agent.
        Give 0 if game still running, otherwise 1 for winner and -1 for loser.
        """
        reward = 0
        game_ended = any(
            observations[agent]["is_winner"]
            for agent in [self.agent_name, self.npc.name]
        )
        if game_ended:
            reward = 1 if observations[self.agent_name]["is_winner"] else -1
        return reward

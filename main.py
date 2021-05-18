# -*- coding: utf-8 -*-
"""
Created on Tue Mar  2 02:14:44 2021

@author: karig
"""

from collections import deque
import network_pytorch
import environment
import numpy as np
import torch
import os

#min max scaling function
def MM_scaler(s):
    x= np.zeros(s.shape)
    for i in range(len(s)):
        x[i]=(s[i]-np.min(s[i],axis=0))/((np.max(s[i],axis=0)-np.min(s[i],axis=0))+1e-5)
    return x

def softmax(z):
    softmax = torch.nn.Softmax(0)
    return softmax(z)

def selecting(z):
    softmax_z = softmax(z)
    selected = softmax_z[:,0].multinomial(num_samples = num_of_asset, replacement = False)
    selected = selected.cpu().numpy()
    xi_z = deque()
    selected_index = torch.zeros(s.shape[0])
    for i in selected:
        xi_z.append(z[i])
        selected_index[i] = 1
    xi_z = torch.tensor(xi_z)
    inverse_sumz = selected_index/torch.sum(torch.exp(xi_z))
    weight = softmax(xi_z)
    
    return selected, weight, inverse_sumz

#preprocessed data loading
is_train = True
is_save = True
load_weight = 0

#hyperparameters
input_day_size = 50
filter_size = 3
num_of_feature = 4
num_of_asset = 10
num_episodes = 5000 if is_train ==1 else 1
money = 1e+8
sensivity = 0.4

#model
save_frequency = 10

use_cuda = torch.cuda.is_available()
cuda_index = torch.device('cuda:0') 
save_path = 'd:/data/weights/'
load_list = os.listdir(save_path)

env = environment.trade_env(number_of_asset = num_of_asset)

s=env.reset()
iteration = 0
loss = 0.

agent = network_pytorch.Agent(s.shape, beta = sensivity)
agent = agent.cuda()

if load_weight:
    agent.load_state_dict(torch.load(save_path+load_list[-1]))
    #agent = torch.load(save_path+load_list[-1])
    print(load_list[-1], 'loaded')
    iteration = int(load_list[-1])
    agent.eval()
    if is_train:
        agent.train()


for i in range(iteration,num_episodes):
    s=env.reset()
    s=MM_scaler(s)
    done=False
    v=money
    while not done:
        mu, sigma, z = agent.predict(torch.tensor(s, dtype = torch.float).cuda())
        selected_index, weight, selected_z = selecting(z)
        selected_s = env.select_from_index(selected_index)
        s_prime, r, done, v, growth = env.step(weight.numpy())
        s_prime = MM_scaler(s_prime)
        agent.calculate_loss(z , selected_z, mu, sigma, torch.tensor(growth).cuda())
        s = s_prime
        if done:
            loss += torch.sum(agent.loss).item()
            agent.optimize()
            print('%d agent: %.4f benchmark: %.4f, alloc: %.4f dist: %.4f'%(i,v/money,env.benchmark/money,torch.sum(agent.alloc_loss).item(),torch.sum(agent.dist_loss).item()))
            
    if i % save_frequency == 0 and is_save == True and i !=0:
        torch.save(agent.state_dict(), save_path + str(i).zfill(4)+'.pt')
        print(i, 'saved loss: %.4f'%loss)
        loss = 0.
# -*- coding: utf-8 -*-
"""WGAN.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Z0H7ZERHz1yuzcI1QWKfYb3-Amoru5hb
"""

import torch
import torch.nn as nn
import torchvision
import torch.optim as optim
from torch.autograd import Variable
import torchvision.utils as vutils
import torchvision.datasets as datasets
import torchvision.transforms as transforms
import matplotlib.pyplot as plt

# initialize Parameters
learning_rate = 0.0002
size_of_batch = 64
num_epochs = 10
critic_iter = 5
noise_dim = 100
output_folder="./WGANOutput"

# Get CIFAR10 Dataset
data_set = datasets.CIFAR10(root="./data", download=False, transform=transforms.Compose([
    transforms.Resize(64),transforms.ToTensor(), transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),]))
data_loader = torch.utils.data.DataLoader(data_set, batch_size = 128, shuffle=True, num_workers=2)

# initializing the weights for generator and discriminator
def weights_init(m):
    classname = m.__class__.__name__
    if classname.find('Conv') != -1:
        m.weight.data.normal_(0.0, 0.02)
    elif classname.find('BatchNorm') != -1:
        m.weight.data.normal_(1.0, 0.02)
        m.bias.data.fill_(0)

# Create Discriminator Class
class Discriminator(nn.Module):
    def __init__(self):
        super(Discriminator,self).__init__()
        self.main=nn.Sequential(
            nn.Conv2d(3, 64, 4, 2, 1),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv2d(64, 128, 4, 2, 1),
            nn.BatchNorm2d(128),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv2d(128, 256, 4, 2, 1),
            nn.BatchNorm2d(256),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv2d(256, 512, 4, 2, 1),
            nn.BatchNorm2d(512),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv2d(512, 1, 4, 1, 0),
        )
    def forward(self, passedInput):
        return self.main(passedInput).mean(0).view(1)

# Create Generator Class
class Generator(nn.Module):
    def __init__(self):
        super(Generator,self).__init__()
        self.main=nn.Sequential(
            nn.ConvTranspose2d(noise_dim, 512, 4, 1, 0, bias=False),
            nn.BatchNorm2d(512),
            nn.ReLU(True),
            nn.ConvTranspose2d(512, 256, 4, 2, 1, bias=False),
            nn.BatchNorm2d(256),
            nn.ReLU(True),
            nn.ConvTranspose2d(256, 128, 4, 2, 1, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(True),
            nn.ConvTranspose2d(128, 64, 4, 2, 1, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(True),
            nn.ConvTranspose2d(64, 3, 4, 2, 1, bias=False),
            nn.Tanh()
        )
    def forward(self, passedInput):
        return self.main(passedInput)

# Create Generator object
discriminator = Discriminator()
# Create Discriminator object
generator = Generator()
#apply initial weights
discriminator.apply(weights_init)
generator.apply(weights_init)
discriminator
generator

# Optimizers
dis_optim = optim.RMSprop(discriminator.parameters(),lr=learning_rate)
gen_optim = optim.RMSprop(generator.parameters(),lr=learning_rate)
criterion = nn.BCELoss()

# Initialize the parameters for training
real_value = 1
fake_value = 0
input_tensor = torch.FloatTensor(size_of_batch, 3, 64, 64)
noise = torch.FloatTensor(size_of_batch, noise_dim, 1, 1)
norm_noise = torch.FloatTensor(size_of_batch, noise_dim, 1, 1).normal_(0, 1)
norm_noise = Variable(norm_noise)
ones_tensor = torch.FloatTensor([1])
nOnesTensor=ones_tensor * (-1)
criterion.cuda()


# arrays for storing training losses and tracking progress
disc_loss_list = []
gen_loss_list = []
count_list = []
count = 0

# Training algorithm for discriminator and generator
for epoch in range(num_epochs):
    epochData = iter(data_loader)
    data_counter = 0
    
    # Iterate for all batches of data
    while data_counter < len(data_loader):
        for param in discriminator.parameters():
            param.requires_grad=True
        
        # Iterate until critic requirement is satisfied
        critic_counter = 0
        while data_counter < len(data_loader) and critic_counter < critic_iter:
            data = epochData.next()
            critic_counter += 1
            for param in discriminator.parameters():
                param.data.clamp_(-1e-2, 1e-2)
            data_counter += 1
            
            # Train Discriminator with real data
            dis_optim.zero_grad()
            real_data, _ = data
            size_of_batch = real_data.size(0)
            real_data = real_data
            input_tensor.resize_as_(real_data).copy_(real_data)
            input_var = Variable(input_tensor)
            dis_real_error = discriminator(input_var)
            dis_real_error.backward(ones_tensor)

            # Train Discriminator on fake data
            noise.resize_(size_of_batch, noise_dim, 1,1).normal_(0,1)
            noise_var = Variable(noise)
            fake_data = generator(noise_var)
            dis_fake_error = discriminator(fake_data.detach())
            dis_fake_error.backward(nOnesTensor)
            dis_optim.step()
            final_dis_error = -dis_fake_error + dis_real_error
            
        # Train Generator
        for param in discriminator.parameters():
            param.requires_grad = False
        gen_optim.zero_grad()
        gen_error = discriminator(fake_data)
        gen_error.backward(ones_tensor)
        gen_optim.step()
        
        
        print('[%d/%d][%d/%d] DLoss: %.4f GLoss: %.4f' % 
             (epoch, num_epochs, data_counter, len(data_loader), final_dis_error.data[0], gen_error.data[0]))

        count += 1
        count_list.append(count)
        gen_loss_list.append(gen_error.data.cpu().numpy()[0])
        disc_loss_list.append(final_dis_error.data.cpu().numpy()[0])
    
    # Store fake images
    fake_data = generator(norm_noise)
    fake_data.data = fake_data.data.mul(0.5).add(0.5)
    vutils.save_image(fake_data.data, '%s/fake_samples_epoch_%03d.png' % 
                      (output_folder, epoch), normalize=True)

# Plot the loss of the generator and the descriminator
# plot predictions for arcsinh(x) and compate to ground truth
plt.plot(count_list, gen_loss_list, 'r.', label='Generator')
plt.plot(count_list, disc_loss_list, 'b.', label='Discriminator')
plt.title("WGAN Loss of Discriminator and Generator")
plt.xlabel("Batch Number")
plt.ylabel("Binary Cross Entropy Loss")
plt.legend(loc = "best")
plt.show()










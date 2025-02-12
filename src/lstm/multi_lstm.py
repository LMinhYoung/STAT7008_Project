import torch
import torch.nn as nn
import torch.nn.functional as F
from .lstmcell import LSTMCell, LSTMCell_

class MultiLayerLSTM(nn.Module):
    """
    MultiLayerLSTM utilizes LSTMCell to implement Multilayer-LSTM
    
    Method:
        forward(self, input_seq, h_0, c_0): allow whole sequence
    """
    
    def __init__(self, input_size, hidden_size, num_layers=1, dropout_rate=0.0):
        super().__init__()
        self.input_size=input_size
        self.hidden_size=hidden_size
        self.num_layers=num_layers
        self.lstm = nn.ModuleList([LSTMCell(self.input_size, self.hidden_size, dropout_rate)])
        for _ in range(1, num_layers):
            self.lstm.append(LSTMCell(self.hidden_size, self.hidden_size, dropout_rate))

    def forward(self, input_seq, h_0=None, c_0=None):
        batch_size = input_seq.size(0)
        
        if h_0 is None:
            h_0 = torch.zeros(self.num_layers, 
                              batch_size, 
                              self.hidden_size, 
                              device=input_seq.device).detach()
        if c_0 is None:
            c_0 = torch.zeros(self.num_layers, 
                              batch_size, 
                              self.hidden_size, 
                              device=input_seq.device).detach()

        hidden_seq, h, c = self.lstm[0](input_seq, h_0[0], c_0[0])
        for i in range(1,self.num_layers):
            hidden_seq, h, c = self.lstm[i](hidden_seq, h_0[i], c_0[i])
        
        return hidden_seq, h, c

class MultiLayerLSTM_(nn.Module):
    """
    MultiLayerLSTM_ utilizes LSTMCell_ to implement Multilayer-LSTM for teacher forcing
    
    Method:
        forward(self, x_t, h_t, c_t): only allow 1 timestamp
    """
    
    def __init__(self, input_size, hidden_size, num_layers=1, dropout_rate=0.0):
        super().__init__()
        self.input_size=input_size
        self.hidden_size=hidden_size
        self.num_layers=num_layers
        self.lstm = nn.ModuleList([LSTMCell_(self.input_size, self.hidden_size, dropout_rate)])
        for _ in range(1, num_layers):
            self.lstm.append(LSTMCell_(self.hidden_size, self.hidden_size, dropout_rate))

    def forward(self, x_t, h_t=None, c_t=None):
        batch_size = x_t.size(0)
        
        if h_t is None:
            h_t = torch.zeros(self.num_layers, 
                              batch_size, 
                              self.hidden_size, 
                              device=x_t.device).detach()
        if c_t is None:
            c_t = torch.zeros(self.num_layers, 
                              batch_size, 
                              self.hidden_size, 
                              device=x_t.device).detach()
        
        # create new tensors and avoid modifying h_t and c_t inplace
        # otherwise backpropagation error will be triggered
        h_t_copy = torch.zeros(self.num_layers, 
                               batch_size, 
                               self.hidden_size, 
                               device=x_t.device)
        c_t_copy = torch.zeros(self.num_layers, 
                               batch_size, 
                               self.hidden_size, 
                               device=x_t.device)
           
        h, c = self.lstm[0](x_t, h_t[0], c_t[0])
        h_t_copy[0], c_t_copy[0] = h, c
        
        for i in range(1,self.num_layers):
            h, c = self.lstm[i](h, h_t[i], c_t[i])
            h_t_copy[i], c_t_copy[i] = h, c
        
        return h, h_t_copy, c_t_copy
    
class LSTM(nn.Module):
    """
    LSTM utilizes MultiLayerLSTM to implement LSTM 
    
    Method:
        forward(self, input_seq, h_0, c_0): allow whole sequence
    """
    
    def __init__(self, input_size, hidden_size, output_size, num_layers=1, dropout_rate=0.0):
        super().__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size
        self.num_layers = num_layers
        self.lstm = MultiLayerLSTM(self.input_size, self.hidden_size, self.num_layers, dropout_rate)
        self.fc = nn.Linear(self.hidden_size, self.output_size)
    
    def forward(self, input_seq, h_0=None, c_0=None):
        batch_size = input_seq.size(0)
        if h_0 is None:
            h_0 = torch.zeros(self.num_layers, 
                              batch_size, 
                              self.hidden_size, 
                              device=input_seq.device).detach() # (num_layer, batch_size, hidden_size)
        if c_0 is None:
            c_0 = torch.zeros(self.num_layers, 
                              batch_size, 
                              self.hidden_size, 
                              device=input_seq.device).detach() # (num_layer, batch_size, hidden_size)

        output, _, _ = self.lstm(input_seq, h_0, c_0) # (batch_size, seq_len, hidden_size)
        batch_size, seq_len, _ = output.shape
        output = output.view(batch_size * seq_len, self.hidden_size) # (batch_size * seq_len, hidden_size)
        output = self.fc(output)
        output = output.view(batch_size, seq_len, self.output_size)
        
        return output

class LSTM_(nn.Module):
    """
    LSTM_ utilizes MultiLayerLSTM_ to implement LSTM for teacher forcing
    
    Method:
        forward(self, input_seq, h_0, c_0): allow whole sequence
    """
    def __init__(self, input_size, hidden_size, output_size, num_layers=1, dropout_rate=0.0):
        super().__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size
        self.num_layers = num_layers
        self.lstm = MultiLayerLSTM_(self.input_size, self.hidden_size, self.num_layers, dropout_rate)
        self.fc = nn.Linear(self.hidden_size, self.output_size)
    
    def forward(self, x_t, h_t=None, c_t=None):
        batch_size = x_t.size(0)
        
        if h_t is None:
            h_t = torch.zeros(self.num_layers, 
                              batch_size, 
                              self.hidden_size, 
                              device=x_t.device).detach() # (num_layer, batch_size, hidden_size)
        if c_t is None:
            c_t = torch.zeros(self.num_layers, 
                              batch_size, 
                              self.hidden_size, 
                              device=x_t.device).detach() # (num_layer, batch_size, hidden_size)
        
        output, h_t, c_t = self.lstm(x_t, h_t, c_t) # h: (batch_size, hidden_size), h_t, c_t: (num_layer, batch_size, hidden_size)
        output = self.fc(output) # (batch_size, output_size)
        
        return output, h_t, c_t

class LSTMDecoder(nn.Module):
    """
    LSTMDecoder utilizes LSTM_ to implement LSTM Decoder with teacher forcing
    
    Method:
        forward(self, x_t, h_t, c_t): only allow 1 timestamp
    """
    def __init__(self, input_size, hidden_size, output_size, tgt_embedding, num_layers=1, dropout_rate=0.0):
        super().__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size
        self.tgt_embedding = tgt_embedding
        self.num_layers = num_layers
        self.lstm = LSTM_(self.input_size, self.hidden_size, self.output_size, self.num_layers, dropout_rate)
        
    def forward(self, input_seq, h_encode, c_encode, teacher_forcing_ratio=0, temperature=1.0):
        batch_size, seq_len, _ = input_seq.size()
        use_teacher_forcing = torch.rand(1).item() < teacher_forcing_ratio
        outputs = []
        predicted_tokens = []
        finished = torch.zeros(batch_size, dtype=torch.bool, device=input_seq.device)
        input_seq = input_seq.transpose(1, 0) # (seq_len, batch_size, input_size)
        current_input = input_seq[0, :, :] # (batch_size, input_size)
        for t in range(seq_len):
            x_t = current_input
            output_t, h_encode, c_encode = self.lstm(x_t, h_encode, c_encode) # h_t, c_t: (num_layer, batch_size, hidden_size)
            logits = output_t / temperature
            probabilities = F.softmax(logits, dim=1)
            predicted_token = torch.multinomial(probabilities, num_samples=1).squeeze() # (batch_size,)
            for i, finish in enumerate(finished):
                if finish:
                    # output_t[i].fill_(-1e10) # 将所有logits设为负无穷
                    # output_t[i, 0] = 0 # 将填充符位置的logit设为0
                    # # output_t[i] = output_tensor
                    predicted_token[i] = 0
                elif not finish and predicted_token[i] == 3:
                    finished[i] = True
            outputs.append(output_t.unsqueeze(1)) # (batch_size, 1, output_size)
            predicted_tokens.append(predicted_token.unsqueeze(1))
            # print(finished[:3])
            if t < seq_len - 1 and use_teacher_forcing:
                current_input = input_seq[t + 1, :, :]
            else: # temperature sampling
                # print('-'*100)
                # print(predicted_token[:5])
                # print('-'*100)
                current_input = self.tgt_embedding(predicted_token) # (batch_size, input_size)
         
        outputs = torch.cat(outputs, dim=1)  # (batch_size, seq_len, output_size)
        predicted_tokens = torch.cat(predicted_tokens, dim=1)
        
        return outputs, predicted_tokens
    